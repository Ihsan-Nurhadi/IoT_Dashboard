/**
 * GOOGLE APPS SCRIPT: NMS Mitratel Hourly Matrix Monitoring Sync
 * 
 * PEMBARUAN TERBARU:
 * 1. Otomatis Mengurutkan Kolom Jam secara Kronologis (00:00, 01:00, ..., 06:00, 07:00, 08:00, dst.).
 * 2. Jam 07:00 dan 08:00 dijamin selalu berada di sebelah kanan jam 06:00 (bukan di depan 00:00).
 * 3. Tidak ada lagi kolom kosong 24 jam di awal; kolom bertambah dinamis dan langsung terurut.
 * 4. Summary hanya 1 blok tetap (Row 64-66) yang selalu update in-place.
 * 5. Menu '⚡ NMS Mitratel' di toolbar untuk 1-klik merapikan & mengurutkan semua sheet.
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

    var numSites = (sites && sites.length > 0) ? sites.length : 61;

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

    // 3. Tentukan Jam Masuk Saat Ini secara Angka (0 s.d 23)
    var currentHourNum = parseHourToNumber(hourStr);
    if (currentHourNum === -1) {
      currentHourNum = (new Date()).getHours();
    }
    var cleanHour = (currentHourNum < 10 ? "0" : "") + currentHourNum + ":00";

    // 4. Cari Kolom untuk Jam Ini
    var targetColIndex = -1;
    var lastCol = sheet.getLastColumn();

    if (lastCol >= 6) {
      var headerDisplays = sheet.getRange(1, 1, 1, lastCol).getDisplayValues()[0];
      for (var c = 5; c < headerDisplays.length; c++) {
        var colHour = parseHourToNumber(headerDisplays[c]);
        if (colHour === currentHourNum) {
          targetColIndex = c + 1;
          break;
        }
      }
    }

    // Jika kolom jam ini belum ada, tambahkan di paling kanan terlebih dahulu
    if (targetColIndex === -1) {
      targetColIndex = sheet.getLastColumn() + 1;
      sheet.getRange(1, targetColIndex)
        .setNumberFormat("@")
        .setValue(cleanHour)
        .setBackground("#2C5E8A")
        .setFontColor("#FFFFFF")
        .setFontWeight("bold")
        .setHorizontalAlignment("center")
        .setVerticalAlignment("middle");
      sheet.setColumnWidth(targetColIndex, 85);
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

    // 8. URUTKAN ULANG SEMUA KOLOM JAM SECARA KRONOLOGIS (00:00 -> 23:00)
    sortAndDeduplicateHourColumns(sheet, numSites);

    return ContentService.createTextOutput(JSON.stringify({
      status: "success",
      message: "Berhasil update status jam " + cleanHour + " untuk " + sites.length + " site (Kolom terurut kronologis).",
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
// 2. HELPER: PARSING JAM STRING KE INTEGER (0 s.d 23)
// ==============================================================================
function parseHourToNumber(hourStr) {
  if (hourStr === null || hourStr === undefined) return -1;
  var s = String(hourStr).trim();

  // Jika Google Sheets mengembalikan objek Date (misal "Sat Dec 30 1899 07:00:00 GMT+...")
  if (s.indexOf("GMT") > -1 || s.indexOf("1899") > -1) {
    try {
      var d = new Date(hourStr);
      if (!isNaN(d.getTime())) {
        return d.getHours();
      }
    } catch (e) {}
  }

  // Format "HH:mm" atau "H:mm" (contoh: "07:00", "7:00", "0:00", "00:00")
  var match = s.match(/^(\d{1,2}):/);
  if (match) {
    return parseInt(match[1], 10);
  }

  // Jika hanya format angka jam (misal 7 atau "07")
  var num = parseInt(s, 10);
  if (!isNaN(num) && num >= 0 && num <= 23) {
    return num;
  }

  return -1;
}

// ==============================================================================
// 3. FUNGSI UTAMA: MENGURUTKAN KRONOLOGIS & MENGHAPUS KOLOM DUPLIKAT/KOSONG
// ==============================================================================
function sortAndDeduplicateHourColumns(sheet, numSites) {
  if (!sheet) return;
  numSites = numSites || 61;
  var lastCol = sheet.getLastColumn();
  if (lastCol < 6) return;

  var totalRows = numSites + 1; // Baris 1 (header) s.d Baris 62 (site terakhir)
  var numCols = lastCol - 5;    // Jumlah kolom jam yang ada saat ini

  // Baca seluruh data kolom jam yang ada
  var hourRange = sheet.getRange(1, 6, totalRows, numCols);
  var values = hourRange.getValues();
  var displayValues = hourRange.getDisplayValues();
  var bgColors = hourRange.getBackgrounds();
  var fontColors = hourRange.getFontColors();
  var fontWeights = hourRange.getFontWeights();
  var alignments = hourRange.getHorizontalAlignments();

  var parsedCols = [];

  for (var c = 0; c < numCols; c++) {
    var rawHeader = String(displayValues[0][c]).trim();
    var hourNum = parseHourToNumber(rawHeader);

    // Abaikan jika bukan kolom jam
    if (hourNum === -1) continue;

    var hasData = false;
    var colValues = [];
    var colBgs = [];
    var colFonts = [];
    var colWeights = [];
    var colAligns = [];

    // Format header jam standar dengan 2 digit: "00:00", "01:00", ..., "07:00", ..., "23:00"
    var formattedHeader = (hourNum < 10 ? "0" : "") + hourNum + ":00";
    colValues.push(formattedHeader);
    colBgs.push("#2C5E8A");
    colFonts.push("#FFFFFF");
    colWeights.push("bold");
    colAligns.push("center");

    for (var r = 1; r < totalRows; r++) {
      var val = String(values[r][c]).trim().toUpperCase();
      if (val === "ONLINE" || val === "OFFLINE") {
        hasData = true;
      }
      colValues.push(val || "-");
      colBgs.push(bgColors[r][c] || "#FFFFFF");
      colFonts.push(fontColors[r][c] || "#000000");
      colWeights.push(fontWeights[r][c] || "bold");
      colAligns.push(alignments[r][c] || "center");
    }

    // Abaikan kolom yang kosong (tidak ada status ONLINE maupun OFFLINE)
    if (!hasData) continue;

    parsedCols.push({
      hourNum: hourNum,
      header: formattedHeader,
      values: colValues,
      bgColors: colBgs,
      fontColors: colFonts,
      fontWeights: colWeights,
      alignments: colAligns
    });
  }

  if (parsedCols.length === 0) return;

  // Deduplikasi: jika ada 2 kolom dengan jam yang sama, gunakan yang terbaru
  var uniqueMap = {};
  for (var i = 0; i < parsedCols.length; i++) {
    uniqueMap[parsedCols[i].hourNum] = parsedCols[i];
  }

  // Urutkan secara kronologis (0, 1, 2, ..., 23)
  var sortedCols = [];
  for (var h = 0; h <= 23; h++) {
    if (uniqueMap[h]) {
      sortedCols.push(uniqueMap[h]);
    }
  }

  // Susun matriks 2D untuk ditulis kembali ke sheet
  var newValues = [];
  var newBgs = [];
  var newFonts = [];
  var newWeights = [];
  var newAligns = [];

  for (var r = 0; r < totalRows; r++) {
    newValues.push([]);
    newBgs.push([]);
    newFonts.push([]);
    newWeights.push([]);
    newAligns.push([]);
    for (var c = 0; c < sortedCols.length; c++) {
      newValues[r].push(sortedCols[c].values[r]);
      newBgs[r].push(sortedCols[c].bgColors[r]);
      newFonts[r].push(sortedCols[c].fontColors[r]);
      newWeights[r].push(sortedCols[c].fontWeights[r]);
      newAligns[r].push(sortedCols[c].alignments[r]);
    }
  }

  // Tulis kembali seluruh kolom yang sudah terurut rapi
  var writeRange = sheet.getRange(1, 6, totalRows, sortedCols.length);
  writeRange.setNumberFormat("@");
  writeRange.setValues(newValues);
  writeRange.setBackgrounds(newBgs);
  writeRange.setFontColors(newFonts);
  writeRange.setFontWeights(newWeights);
  writeRange.setHorizontalAlignments(newAligns);
  writeRange.setFontFamily("Calibri");
  writeRange.setFontSize(10);

  // Atur lebar kolom jam rapi (85px)
  for (var k = 0; k < sortedCols.length; k++) {
    sheet.setColumnWidth(6 + k, 85);
  }

  // Jika sebelumnya ada kolom sisa di sebelah kanan, hapus kolom-kolom berlebih tersebut
  var remainingCols = sheet.getLastColumn() - (5 + sortedCols.length);
  if (remainingCols > 0) {
    sheet.deleteColumns(6 + sortedCols.length, remainingCols);
  }
}

// ==============================================================================
// 4. FUNGSI MERAPIKAN SELURUH SHEET (HARI SEBELUMNYA DAN HARI INI)
// ==============================================================================
function cleanupAllSheets() {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var sheets = ss.getSheets();
  var totalProcessed = 0;
  var details = [];

  for (var i = 0; i < sheets.length; i++) {
    var sh = sheets[i];
    if (sh.getLastRow() >= 2 && sh.getLastColumn() >= 6) {
      sortAndDeduplicateHourColumns(sh, 61);
      totalProcessed++;
      details.push(sh.getName());
    }
  }

  return {
    totalProcessed: totalProcessed,
    details: details
  };
}

// ==============================================================================
// 5. MENU TOOLBAR SPREADSHEET (1-Klik Rapikan Semua Sheet)
// ==============================================================================
function onOpen() {
  try {
    SpreadsheetApp.getUi()
      .createMenu("⚡ NMS Mitratel")
      .addItem("🔄 Urutkan & Bersihkan Kolom Jam (Semua Sheet)", "menuCleanupAll")
      .addToUi();
  } catch (e) {}
}

function menuCleanupAll() {
  var res = cleanupAllSheets();
  var ui = SpreadsheetApp.getUi();
  ui.alert(
    "Pengurutan Kolom Selesai",
    "Berhasil merapikan dan mengurutkan kolom jam secara kronologis (00:00 s.d 23:00) pada sheet:\n\n" + res.details.join("\n"),
    ui.ButtonSet.OK
  );
}

// ==============================================================================
// 6. WEBHOOK GET (Bisa Dibuka di Browser untuk Otomatis Urutkan Semua Sheet)
// ==============================================================================
function doGet(e) {
  var cleanRes = cleanupAllSheets();

  return ContentService.createTextOutput(
    "=====================================================\n" +
    "  NMS MITRATEL WEBHOOK & AUTO-SORT ACTIVE\n" +
    "=====================================================\n\n" +
    "Hasil Pengurutan & Pembersihan Kolom Seluruh Sheet:\n" +
    "- Total Sheet Diproses : " + cleanRes.totalProcessed + "\n" +
    "- Sheet yang Dirapikan : " + cleanRes.details.join(", ") + "\n\n" +
    "Keterangan:\n" +
    "✓ Jam 07:00 dan 08:00 sudah dipindahkan ke samping kanan jam 06:00.\n" +
    "✓ Seluruh kolom jam sekarang terurut secara kronologis (00:00 -> 23:00).\n" +
    "✓ Kolom kosong & duplikat telah dibersihkan otomatis."
  );
}
