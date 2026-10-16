/**
 * GOOGLE APPS SCRIPT: NMS Mitratel Hourly Matrix Monitoring Sync
 * 
 * PEMBARUAN:
 * 1. Tidak lagi membuat 24 kolom jam kosong (00:00 - 23:00) di awal!
 * 2. Kolom jam hanya dibuat secara dinamis saat data jam tersebut tiba, dan diurutkan kronologis.
 * 3. Fitur Pembersihan Otomatis (Cleanup): Menghapus seluruh kolom jam kosong untuk hari sebelumnya maupun ke depannya.
 * 4. Menu Spreadsheet: Menu '⚡ NMS Mitratel' di toolbar untuk 1-klik membersihkan kolom kosong semua sheet.
 * 5. Summary hanya 1 blok tetap (Row 64-66) yang selalu update in-place.
 * 
 * CARA UPDATE (Hanya 1 Menit):
 * 1. Buka Google Spreadsheet Anda.
 * 2. Di menu atas: Extensions (Ekstensi) > Apps Script.
 * 3. Hapus semua isi kode lama, paste SELURUH kode di bawah ini.
 * 4. Tekan Ctrl+S (ikon simpan).
 * 5. Klik Deploy > Manage deployments > Edit (ikon pensil) > Version: New version > Klik Deploy.
 */

// ==============================================================================
// 1. WEBHOOK POST (Menerima Data Tiap Jam dari Monitoring Mitratel)
// ==============================================================================
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

    // 2. Inisialisasi Header Dasar (HANYA 5 KOLOM METADATA, TANPA KOLOM JAM KOSONG!)
    if (isNew || sheet.getLastRow() < 2) {
      sheet.clear();

      // Header Baris 1: Hanya 5 kolom metadata dasar
      var baseHeaders = ["No", "Site ID", "Nama Site", "Regional", "Client ID (MQTT)"];
      sheet.getRange(1, 1, 1, baseHeaders.length).setValues([baseHeaders]);

      // Styling Header Utama
      var headerRange = sheet.getRange(1, 1, 1, baseHeaders.length);
      headerRange.setBackground("#1B365D");
      headerRange.setFontColor("#FFFFFF");
      headerRange.setFontWeight("bold");
      headerRange.setHorizontalAlignment("center");
      headerRange.setVerticalAlignment("middle");
      sheet.setRowHeight(1, 32);

      // Tulis baris dasar seluruh 61 site
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

        // Alignment kolom metadata
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

    // Hitung jumlah site murni (default 61 site Mitratel)
    var numSites = (sites && sites.length > 0) ? sites.length : 61;

    // 3. Bersihkan kolom kosong/duplikat terlebih dahulu sebelum memproses jam ini
    cleanupSheetColumns(sheet, numSites);

    // 4. Cari atau Sisipkan Kolom untuk Jam Ini (misal: "18:00")
    var cleanHour = hourStr.indexOf(":") > -1 ? hourStr.split(":")[0] + ":00" : hourStr;
    var targetColIndex = -1;
    var lastCol = sheet.getLastColumn();

    // A. Cari apakah kolom jam ini sudah ada sebelumnya (Gunakan getDisplayValues agar akurat)
    if (lastCol >= 6) {
      var headerDisplays = sheet.getRange(1, 1, 1, lastCol).getDisplayValues()[0];
      for (var c = 5; c < headerDisplays.length; c++) {
        var colHeader = String(headerDisplays[c]).trim();
        if (colHeader === cleanHour) {
          targetColIndex = c + 1;
          break;
        }
      }
    }

    // B. Jika kolom jam ini belum ada, sisipkan secara terurut kronologis (00:00 s.d 23:00)
    if (targetColIndex === -1) {
      var inserted = false;
      if (lastCol >= 6) {
        var headerDisplays = sheet.getRange(1, 1, 1, lastCol).getDisplayValues()[0];
        for (var c = 5; c < headerDisplays.length; c++) {
          var colHeader = String(headerDisplays[c]).trim();
          // Jika kolom berisi format jam dan nilainya lebih besar, sisipkan sebelum kolom tersebut
          if (colHeader.indexOf(":") > -1 && colHeader > cleanHour) {
            sheet.insertColumnBefore(c + 1);
            targetColIndex = c + 1;
            inserted = true;
            break;
          }
        }
      }

      // Jika tidak ada kolom jam yang lebih besar, tambahkan di paling kanan
      if (!inserted) {
        targetColIndex = sheet.getLastColumn() + 1;
      }

      // Format header kolom jam baru sebagai plain text (@) agar tidak dikonversi ke Date
      sheet.getRange(1, targetColIndex)
        .setNumberFormat("@")
        .setValue(cleanHour)
        .setBackground("#2C5E8A")
        .setFontColor("#FFFFFF")
        .setFontWeight("bold")
        .setHorizontalAlignment("center")
        .setVerticalAlignment("middle");
      sheet.setColumnWidth(targetColIndex, 90);
    }

    // 5. Baca Mapping Site ID & Client ID yang Ada di Sheet
    var existingMeta = sheet.getRange(2, 2, numSites, 4).getValues(); // Col 2 (Site ID) s.d Col 5 (Client ID)
    var rowLookup = {};
    for (var r = 0; r < existingMeta.length; r++) {
      var sId = String(existingMeta[r][0]).trim().toUpperCase();
      var sName = String(existingMeta[r][1]).trim().toUpperCase();
      var cId = String(existingMeta[r][3]).trim().toUpperCase();
      if (sId) rowLookup[sId] = r + 2;
      if (sName) rowLookup[sName] = r + 2;
      if (cId) rowLookup[cId] = r + 2;
    }

    // 6. Update Status Setiap Site pada Kolom Jam Tersebut
    var statusUpdates = [];
    var bgColors = [];
    var fontColors = [];

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

    // Tulis status site HANYA pada rentang baris 2 s.d (numSites + 1)
    var targetCellRange = sheet.getRange(2, targetColIndex, numSites, 1);
    targetCellRange.setValues(statusUpdates);
    targetCellRange.setBackgrounds(bgColors);
    targetCellRange.setFontColors(fontColors);
    targetCellRange.setFontWeight("bold");
    targetCellRange.setFontFamily("Calibri");
    targetCellRange.setFontSize(10);
    targetCellRange.setHorizontalAlignment("center");
    targetCellRange.setVerticalAlignment("middle");

    // 7. Summary: HANYA 1 BLOK TETAP DI BAWAH TABEL (Row 64 s.d 66)
    var summaryRow = numSites + 3; // Baris 64 untuk 61 site

    // Bersihkan baris-baris berlebih di bawahnya jika ada sisa duplikasi
    var maxSheetRows = sheet.getLastRow();
    if (maxSheetRows > (summaryRow + 2)) {
      sheet.getRange(summaryRow + 3, 1, maxSheetRows - (summaryRow + 2), sheet.getLastColumn()).clear();
    }

    // Bersihkan kolom jam di samping summary agar area bawah tetap bersih
    if (sheet.getLastColumn() >= 6) {
      sheet.getRange(summaryRow, 6, 3, sheet.getLastColumn() - 5).clear();
    }

    // Pastikan lebar kolom Nama Site cukup
    if (sheet.getColumnWidth(3) < 210) {
      sheet.setColumnWidth(3, 210);
    }

    // Tulis nilai summary jam terkini di baris yang sama persis
    sheet.getRange(summaryRow, 3).setValue("Total Online (" + cleanHour + "):").setFontWeight("bold");
    sheet.getRange(summaryRow, 4).setValue(summary.online != null ? summary.online : 0)
      .setFontWeight("bold").setFontColor("#2E7D32").setHorizontalAlignment("center");

    sheet.getRange(summaryRow + 1, 3).setValue("Total Offline (" + cleanHour + "):").setFontWeight("bold");
    sheet.getRange(summaryRow + 1, 4).setValue(summary.offline != null ? summary.offline : 0)
      .setFontWeight("bold").setFontColor("#C62828").setHorizontalAlignment("center");

    sheet.getRange(summaryRow + 2, 3).setValue("Availability Rate:").setFontWeight("bold");
    sheet.getRange(summaryRow + 2, 4).setValue(summary.availability || "0%")
      .setFontWeight("bold").setHorizontalAlignment("center");

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

// ==============================================================================
// 2. FUNGSI PEMBERSIH KOLOM KOSONG & DUPLIKAT PADA SATU SHEET
// ==============================================================================
function cleanupSheetColumns(sheet, numSites) {
  if (!sheet) return 0;
  numSites = numSites || 61;
  var lastCol = sheet.getLastColumn();
  if (lastCol < 6) return 0;

  var deletedCount = 0;
  var seenHours = {};

  // Periksa dari kolom paling kanan ke kiri agar index kolom stabil saat dihapus
  for (var c = lastCol; c >= 6; c--) {
    var rawHeader = sheet.getRange(1, c).getDisplayValue().trim();
    var cleanHeader = rawHeader.indexOf(":") > -1 ? rawHeader.split(":")[0] + ":00" : rawHeader;

    // Periksa isi data status site pada baris 2 s.d (numSites + 1)
    var vals = sheet.getRange(2, c, numSites, 1).getValues();
    var hasValidData = false;

    for (var r = 0; r < vals.length; r++) {
      var cellVal = String(vals[r][0]).trim().toUpperCase();
      if (cellVal === "ONLINE" || cellVal === "OFFLINE") {
        hasValidData = true;
        break;
      }
    }

    // Kasus 1: Kolom jam ini KOSONG (tidak ada data status ONLINE/OFFLINE)
    if (!hasValidData) {
      sheet.deleteColumn(c);
      deletedCount++;
      continue;
    }

    // Kasus 2: Kolom jam DUPLIKAT (jam sama yang pernah tercatat di kolom lebih kanan)
    if (cleanHeader && cleanHeader.indexOf(":") > -1) {
      if (seenHours[cleanHeader]) {
        sheet.deleteColumn(c);
        deletedCount++;
        continue;
      } else {
        seenHours[cleanHeader] = true;
      }
    }
  }

  return deletedCount;
}

// ==============================================================================
// 3. FUNGSI PEMBERSIH UNTUK SELURUH SHEET (HARI SEBELUMNYA DAN HARI INI)
// ==============================================================================
function cleanupAllSheets() {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var sheets = ss.getSheets();
  var totalDeleted = 0;
  var details = [];

  for (var i = 0; i < sheets.length; i++) {
    var sh = sheets[i];
    if (sh.getLastRow() >= 2 && sh.getLastColumn() >= 6) {
      var del = cleanupSheetColumns(sh, 61);
      if (del > 0) {
        totalDeleted += del;
        details.push(sh.getName() + " (" + del + " kolom)");
      }
    }
  }

  return {
    totalDeleted: totalDeleted,
    details: details
  };
}

// ==============================================================================
// 4. MENU TOOLBAR SPREADSHEET (1-Klik Bersihkan Semua Sheet)
// ==============================================================================
function onOpen() {
  try {
    SpreadsheetApp.getUi()
      .createMenu("⚡ NMS Mitratel")
      .addItem("🧹 Bersihkan Kolom Kosong & Duplikat (Semua Sheet)", "menuCleanupAll")
      .addToUi();
  } catch (e) {}
}

function menuCleanupAll() {
  var res = cleanupAllSheets();
  var ui = SpreadsheetApp.getUi();
  if (res.totalDeleted > 0) {
    ui.alert(
      "Pembersihan Sukses",
      "Berhasil menghapus total " + res.totalDeleted + " kolom kosong/duplikat dari sheet:\n\n" + res.details.join("\n"),
      ui.ButtonSet.OK
    );
  } else {
    ui.alert(
      "Sudah Bersih",
      "Seluruh sheet (hari ini dan hari sebelumnya) sudah rapi! Tidak ditemukan kolom kosong atau duplikat.",
      ui.ButtonSet.OK
    );
  }
}

// ==============================================================================
// 5. WEBHOOK GET (Bisa Dibuka di Browser untuk Otomatis Bersihkan Semua Sheet)
// ==============================================================================
function doGet(e) {
  var cleanRes = cleanupAllSheets();

  return ContentService.createTextOutput(
    "=====================================================\n" +
    "  NMS MITRATEL WEBHOOK & CLEANUP SERVICE ACTIVE\n" +
    "=====================================================\n\n" +
    "Hasil Pembersihan Otomatis Seluruh Sheet:\n" +
    "- Total kolom kosong/duplikat dihapus : " + cleanRes.totalDeleted + "\n" +
    (cleanRes.details.length > 0
      ? "- Rincian per Sheet : " + cleanRes.details.join(", ") + "\n\n"
      : "- Seluruh sheet tanggal sebelumnya & hari ini sudah bersih!\n\n") +
    "Keterangan:\n" +
    "- Ke depannya kolom jam kosong 24 jam tidak akan pernah dibuat lagi.\n" +
    "- Kolom jam hanya akan ditambahkan saat jam tersebut menerima data."
  );
}
