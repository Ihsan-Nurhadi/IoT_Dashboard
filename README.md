Berikut adalah untuk menjalankan program ini :
- Backend
1. Di dalam root folder buat virtual environtment dengan misal : python -m venv myvenv
2. Aktifkan venv dengan "myvenv\Scripts\activate"
3. Jika ada error tandanya windows memblokir hal tersebut bisa difix dengan masuk ke powershell as administrator dan ketik script ini "Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser"
4. Setelah diaktifkan masuk ke file backend di NMS_Backend
5. install dependencies dengan cara "pip install -r requirements.txt"
6. Lalu jalankan program dengan "python manage.py runserver"

- Front end
Setelah backend jalan kita jalankan juga frontend dengan cara:
1. Masuk ke file NMS_IoT
2. lalu install library dengan npm install
3. lalu jalankan dengan npm run dev
# IoT_Dashboard
