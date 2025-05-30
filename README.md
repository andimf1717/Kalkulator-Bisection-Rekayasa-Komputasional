# Kalkulator Bisection Metode Bagi Dua

## Deskripsi Proyek

Program ini merupakan implementasi dari metode bagi dua (Bisection Method) untuk menemukan akar dari suatu persamaan non-linear f(x) = 0. Aplikasi ini dikembangkan menggunakan bahasa pemrograman Python dan dilengkapi dengan antarmuka pengguna grafis (GUI) untuk mempermudah interaksi pengguna dalam memasukkan data dan melihat hasil perhitungan.

## Fitur Utama

* Input persamaan f(x) secara dinamis dengan 'x' sebagai variabel.
* Input parameter metode bagi dua: interval awal [a,b], toleransi error (ε), dan batas maksimum iterasi.
* Pratinjau persamaan dalam format LaTeX untuk verifikasi visual.
* Proses perhitungan akar menggunakan algoritma metode bagi dua.
* Pencatatan detail setiap langkah iterasi untuk analisis proses.
* Tampilan ringkasan hasil perhitungan dalam format tabel.
* Informasi status akhir perhitungan (akar ditemukan, konvergen, atau batas iterasi tercapai).

## Prasyarat Sistem

* Python versi 3.7 atau yang lebih baru.
* PIP (Python package installer), yang umumnya sudah terinstal bersama Python.

## Panduan Instalasi dan Konfigurasi Lingkungan

Untuk menjalankan aplikasi ini, disarankan untuk menggunakan lingkungan virtual (virtual environment) agar dependensi proyek terisolasi dan tidak mengganggu instalasi Python global.

1.  **Memperoleh Kode Sumber:**
    Pastikan Anda telah memiliki semua file proyek, termasuk file skrip Python utama dan file `requirements.txt`. Jika dalam format kompresi (misalnya .zip), ekstrak terlebih dahulu.

2.  **Navigasi ke Direktori Proyek:**
    Buka terminal atau command prompt, kemudian arahkan ke direktori tempat Anda menyimpan file-file proyek.

3.  **Pembuatan Lingkungan Virtual (Direkomendasikan):**
    Jika Anda belum memiliki lingkungan virtual untuk proyek ini, buatlah dengan perintah berikut (Anda hanya perlu melakukannya sekali untuk proyek ini):
    ```bash
    python -m venv env_bisection_calc
    ```
    Perintah di atas akan membuat sebuah folder bernama `env_bisection_calc` (Anda bisa mengganti nama ini jika diinginkan) yang berisi lingkungan virtual.

4.  **Aktivasi Lingkungan Virtual:**
    Setiap kali Anda akan mengerjakan atau menjalankan proyek ini, aktifkan lingkungan virtual terlebih dahulu:
    * **Windows:**
        ```bash
        env_bisection_calc\Scripts\activate
        ```
    * **macOS / Linux:**
        ```bash
        source env_bisection_calc/bin/activate
        ```
    Setelah berhasil, Anda akan melihat nama lingkungan virtual (misalnya `(env_bisection_calc)`) muncul di awal baris perintah terminal Anda.

5.  **Instalasi Dependensi Proyek:**
    Dengan lingkungan virtual yang sudah aktif, instal semua pustaka Python yang dibutuhkan oleh proyek ini menggunakan file `requirements.txt`:
    ```bash
    pip install -r requirements.txt
    ```
    Perintah ini akan menginstal pustaka seperti `customtkinter`, `sympy`, `numpy`, `matplotlib`, dan lainnya yang tercantum dalam file tersebut.

## Cara Menjalankan Aplikasi

Setelah semua langkah instalasi dan konfigurasi di atas selesai, dan lingkungan virtual telah diaktifkan:

1.  Pastikan Anda berada di direktori utama proyek pada terminal.
2.  Jalankan skrip utama aplikasi dengan perintah:
    ```bash
    python bisection_calculator.py
    ```
Antarmuka grafis aplikasi akan ditampilkan.

## Panduan Penggunaan Singkat

1.  **Input Data:** Masukkan persamaan f(x) yang akan dianalisis, nilai interval awal (a dan b), toleransi error, serta batas maksimum iterasi pada kolom yang tersedia.
2.  **Pratinjau (Opsional):** Gunakan tombol "🔄 Pratinjau" untuk melihat representasi LaTeX dari persamaan yang dimasukkan.
3.  **Proses Perhitungan:** Klik tombol "Hitung Akar" untuk memulai proses kalkulasi.
4.  **Analisis Hasil:** Hasil perhitungan akan ditampilkan dalam dua tab:
    * "Detail Perhitungan Iterasi": Menyajikan log langkah-langkah komputasi.
    * "Tabel Ringkasan Iterasi": Menyajikan data ringkas per iterasi beserta kesimpulan akhir.

## Struktur Direktori Proyek (Contoh)
* Nama_Folder_Proyek/
* ├── nama_file_utama.py       # Skrip Python utama aplikasi
* ├── requirements.txt         # Daftar dependensi pustaka
* └── README.md                # File panduan ini
* └── env_bisection_calc/      # Direktori lingkungan virtual (dibuat lokal, tidak untuk didistribusikan)
