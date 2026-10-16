/**
 * GOOGLE APPS SCRIPT: NMS Mitratel Hourly Matrix Monitoring Sync
 * 
 * CARA PEMASANGAN (Hanya 2 Menit):
 * 1. Buka Google Spreadsheet baru atau yang sudah ada untuk monitoring Mitratel.
 * 2. Di menu atas, klik "Extensions" (Ekstensi) > "Apps Script".
 * 3. Hapus semua kode default di editor, lalu PASTE SELURUH KODE DI BAWAH INI.
 * 4. Klik tombol "Save" (ikon disket) atau Ctrl+S.
 * 5. Di kanan atas, klik tombol biru "Deploy" > "New deployment".
 * 6. Pilih type: "Web app" (ikon globe).
 * 7. Isi konfigurasi:
 *    - Description: "Mitratel Hourly Monitor Webhook"
 *    - Execute as: "Me" (email Anda)
 *    - Who has access: "Anyone" (Siapa saja, agar server bisa mengirim data tanpa login browser)
 * 8. Klik "Deploy", izinkan hak akses (Authorize access jika diminta).
 * 9. Salin "Web app URL" (bentuknya: https://script.google.com/macros/s/AKfycb.../exec).
 * 10. Masukkan URL tersebut ke file .env / docker-compose:
 *     GSHEET_WEBHOOK_URL="https://script.google.com/macros/s/AKfycb.../exec"
 */

function doPost(e) {
  try {
    if (!e || !e.postData || !e.postData.contents) {
      return ContentService.createTextOutput(JSON.stringify({
        status: "error",
        message: "No POST payload received"
      })).setMimeType(ContentService.MimeType.JSON);
    }

    var payload = JSON.parse(e.postData.contents);
    var dateStr = payload.date || Utilities.formatDate(new Date(), "Asia/Jakarta", "yyyy-MM-dd");
    var hourStr = payload.hour || Utilities.formatDate(new Date(), "Asia/Jakarta", "HH:00");
    var sites = payload.sites || [];
    var summary = payload.summary || {};

    var ss = SpreadsheetApp.getActiveSpreadsheet();
    var sheet = ss.getSheetByName(dateStr);

    // 1. Jika sheet untuk tanggal hari ini belum ada, buat baru
    var isNew = false;
    if (!sheet) {
      sheet = ss.insertSheet(dateStr, 0);
      isNew = true;
    }

    // 2. Inisialisasi Header dan Metadata Site jika sheet baru
    if (isNew || sheet.getLastRow() < 2) {
      sheet.clear();
      
      // Header Baris 1
      var baseHeaders = ["No", "Site ID", "Nama Site", "Regional", "Client ID (MQTT)"];
      var hourHeaders = [
        "00:00", "01:00", "02:00", "03:00", "04:00", "05:00",
        "06:00", "07:00", "08:00", "09:00", "10:00", "11:00",
        "12:00", "13:00", "14:00", "15:00", "16:00", "17:00",
        "18:00", "19:00", "20:00", "21:00", "22:00", "23:00"
      ];
      var allHeaders = baseHeaders.concat(hourHeaders);
      
      sheet.getRange(1, 1, 1, allHeaders.length).setValues([allHeaders]);
      
      // Styling Header Utama
      var headerRange = sheet.getRange(1, 1, 1, allHeaders.length);
      headerRange.setBackground("#1B365D");
      headerRange.setFontColor("#FFFFFF");
      headerRange.setFontWeight("bold");
      headerRange.setHorizontalAlignment("center");
      headerRange.setVerticalAlignment("middle");
      sheet.setRowHeight(1, 32);

      // Warna pembeda untuk kolom jam
      sheet.getRange(1, 6, 1, hourHeaders.length).setBackground("#2C5E8A");

      // Tulis baris dasar seluruh site
      var rowData = [];
      for (var i = 0; i < sites.length; i++) {
        var s = sites[i];
        rowData.push([
          s.no || (i + 1),
          s.site_id || "",
          s.name || "",
          s.regional || "",
          s.client_id || ""
        ]);
      }
      
      if (rowData.length > 0) {
        sheet.getRange(2, 1, rowData.length, 5).setValues(rowData);
        var metaRange = sheet.getRange(2, 1, rowData.length, 5);
        metaRange.setFontFamily("Calibri");
        metaRange.setFontSize(10);
        metaRange.setVerticalAlignment("middle");
        
        // Alignment
        sheet.getRange(2, 1, rowData.length, 1).setHorizontalAlignment("center"); // No
        sheet.getRange(2, 2, rowData.length, 1).setHorizontalAlignment("center"); // Site ID
        sheet.getRange(2, 3, rowData.length, 1).setHorizontalAlignment("left");   // Name
        sheet.getRange(2, 4, rowData.length, 1).setHorizontalAlignment("center"); // Regional
        sheet.getRange(2, 5, rowData.length, 1).setHorizontalAlignment("left");   // Client ID
      }

      // Freeze baris 1 dan kolom metadata (1-5)
      sheet.setFrozenRows(1);
      sheet.setFrozenColumns(5);
    }

    // 3. Cari Index Kolom untuk Jam Ini (misal: "08:00")
    var lastCol = Math.max(sheet.getLastColumn(), 29);
    var headerValues = sheet.getRange(1, 1, 1, lastCol).getValues()[0];
    var targetColIndex = -1;
    
    // Normalisasi hourStr ke format "HH:00"
    var cleanHour = hourStr.indexOf(":") > -1 ? hourStr.split(":")[0] + ":00" : hourStr;
    
    for (var c = 0; c < headerValues.length; c++) {
      if (String(headerValues[c]).trim() === cleanHour) {
        targetColIndex = c + 1;
        break;
      }
    }

    // Jika kolom jam belum ada di header, tambahkan di akhir
    if (targetColIndex === -1) {
      targetColIndex = sheet.getLastColumn() + 1;
      sheet.getRange(1, targetColIndex).setValue(cleanHour)
        .setBackground("#2C5E8A")
        .setFontColor("#FFFFFF")
        .setFontWeight("bold")
        .setHorizontalAlignment("center");
    }

    // 4. Hitung jumlah site murni (default 61 site Mitratel)
    var numSites = (sites && sites.length > 0) ? sites.length : 61;
    
    // Baca metadata site yang sudah ada di Sheet (hanya baris site, 2 s.d numSites + 1)
    var existingMeta = sheet.getRange(2, 2, numSites, 4).getValues(); // Col 2 (Site ID) to Col 5 (Client ID)
    var rowLookup = {};
    for (var r = 0; r < existingMeta.length; r++) {
      var sId = String(existingMeta[r][0]).trim().toUpperCase();
      var sName = String(existingMeta[r][1]).trim().toUpperCase();
      var cId = String(existingMeta[r][3]).trim().toUpperCase();
      if (sId) rowLookup[sId] = r + 2;
      if (sName) rowLookup[sName] = r + 2;
      if (cId) rowLookup[cId] = r + 2;
    }

    // 5. Update Status Setiap Site pada Kolom Jam Tersebut
    var statusUpdates = [];
    var bgColors = [];
    var fontColors = [];

    // Buat template matriks kosong untuk kolom target (hanya sebanyak jumlah site)
    for (var i = 0; i < numSites; i++) {
      statusUpdates.push(["-"]);
      bgColors.push(["#FFFFFF"]);
      fontColors.push(["#000000"]);
    }

    for (var j = 0; j < sites.length; j++) {
      var site = sites[j];
      var sId = String(site.site_id || "").trim().toUpperCase();
      var cId = String(site.client_id || "").trim().toUpperCase();
      var sName = String(site.name || "").trim().toUpperCase();
      
      var rowIdx = rowLookup[cId] || rowLookup[sId] || rowLookup[sName] || (site.no ? (site.no + 1) : null);
      if (rowIdx && rowIdx >= 2 && rowIdx <= (numSites + 1)) {
        var arrayIndex = rowIdx - 2;
        var st = String(site.status || "-").toUpperCase();
        statusUpdates[arrayIndex] = [st];
        
        if (st === "ONLINE") {
          bgColors[arrayIndex] = ["#E8F5E9"];  // Hijau muda
          fontColors[arrayIndex] = ["#2E7D32"]; // Hijau tua bold
        } else if (st === "OFFLINE") {
          bgColors[arrayIndex] = ["#FFEBEE"];  // Merah muda
          fontColors[arrayIndex] = ["#C62828"]; // Merah tua bold
        } else {
          bgColors[arrayIndex] = ["#F5F5F5"];
          fontColors[arrayIndex] = ["#757575"];
        }
      }
    }

    // Tulis sekaligus status site ke kolom jam target (HANYA rentang site baris 2 s.d numSites + 1)
    var targetCellRange = sheet.getRange(2, targetColIndex, numSites, 1);
    targetCellRange.setValues(statusUpdates);
    targetCellRange.setBackgrounds(bgColors);
    targetCellRange.setFontColors(fontColors);
    targetCellRange.setFontWeight("bold");
    targetCellRange.setFontFamily("Calibri");
    targetCellRange.setFontSize(10);
    targetCellRange.setHorizontalAlignment("center");
    targetCellRange.setVerticalAlignment("middle");

    // 6. Tulis Summary di bawah tabel (BARIS TETAP / IN-PLACE, TIDAK BERTAMBAH KE BAWAH)
    var summaryRow = numSites + 3; // Contoh: untuk 61 site, summaryRow adalah baris 64

    // Bersihkan baris-baris berlebih di bawahnya jika ada sisa duplikasi dari versi sebelumnya
    var maxSheetRows = sheet.getLastRow();
    if (maxSheetRows > (summaryRow + 3)) {
      sheet.getRange(summaryRow + 4, 1, maxSheetRows - (summaryRow + 3), sheet.getLastColumn()).clear();
    }

    // Tulis Label & Angka Terakhir di Kolom C & D (selalu overwrite di baris yang sama persis)
    sheet.getRange(summaryRow, 3).setValue("Total Online:").setFontWeight("bold");
    sheet.getRange(summaryRow, 4).setValue(summary.online != null ? summary.online : 0)
      .setFontWeight("bold").setFontColor("#2E7D32").setHorizontalAlignment("center");
    
    sheet.getRange(summaryRow + 1, 3).setValue("Total Offline:").setFontWeight("bold");
    sheet.getRange(summaryRow + 1, 4).setValue(summary.offline != null ? summary.offline : 0)
      .setFontWeight("bold").setFontColor("#C62828").setHorizontalAlignment("center");

    sheet.getRange(summaryRow + 2, 3).setValue("Availability Rate:").setFontWeight("bold");
    sheet.getRange(summaryRow + 2, 4).setValue(summary.availability || "0%")
      .setFontWeight("bold").setHorizontalAlignment("center");

    sheet.getRange(summaryRow + 3, 3).setValue("Update Terakhir:").setFontWeight("bold");
    sheet.getRange(summaryRow + 3, 4).setValue(cleanHour + " WIB")
      .setFontWeight("bold").setFontColor("#1B365D").setHorizontalAlignment("center");

    // Tulis juga Total Online, Offline, dan Availability Rate pada kolom jam bersangkutan!
    sheet.getRange(summaryRow, targetColIndex).setValue(summary.online != null ? summary.online : 0)
      .setFontWeight("bold").setFontColor("#2E7D32").setHorizontalAlignment("center").setBackground("#E8F5E9");

    sheet.getRange(summaryRow + 1, targetColIndex).setValue(summary.offline != null ? summary.offline : 0)
      .setFontWeight("bold").setFontColor("#C62828").setHorizontalAlignment("center").setBackground("#FFEBEE");

    sheet.getRange(summaryRow + 2, targetColIndex).setValue(summary.availability || "0%")
      .setFontWeight("bold").setHorizontalAlignment("center").setBackground("#F5F5F5");

    return ContentService.createTextOutput(JSON.stringify({
      status: "success",
      message: "Berhasil update status jam " + cleanHour + " untuk " + sites.length + " site.",
      date: dateStr,
      hour: cleanHour,
      online: summary.online,
      offline: summary.offline
    })).setMimeType(ContentService.MimeType.JSON);

  } catch (err) {
    return ContentService.createTextOutput(JSON.stringify({
      status: "error",
      message: err.toString()
    })).setMimeType(ContentService.MimeType.JSON);
  }
}

function doGet(e) {
  return ContentService.createTextOutput("NMS Mitratel Monitoring Webhook is active and running! Send POST request with JSON payload to sync data.");
}
