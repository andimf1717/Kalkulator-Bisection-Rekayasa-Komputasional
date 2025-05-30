import customtkinter as ctk
from tkinter import ttk, messagebox, scrolledtext, font as tkfont
import sympy # Pustaka untuk komputasi simbolik, berguna untuk parsing dan manipulasi ekspresi matematika
from sympy.parsing.sympy_parser import parse_expr, standard_transformations, implicit_multiplication_application, convert_xor # Fungsi spesifik dari sympy untuk parsing
import math # Modul matematika standar Python (untuk fungsi seperti exp, log, sqrt, dll. dalam kalkulasi numerik)
import numpy # Pustaka untuk komputasi numerik, kadang dipakai oleh lambdify untuk fungsi tertentu
import re # Modul regular expression, untuk pencarian pola teks (misalnya di format toleransi)

# Imports untuk Matplotlib Preview
from matplotlib.figure import Figure # Untuk membuat area gambar (figure)
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg # Untuk mengintegrasikan Matplotlib dengan Tkinter
import io # Digunakan untuk menangani stream byte (tidak secara eksplisit dipakai di preview ini, tapi kadang berguna untuk image handling)

# --- Backend Logic --- (Bagian logika inti kalkulator, tidak berhubungan langsung dengan tampilan)

def to_superscript(text_val):
    """Mengubah angka biasa menjadi format superscript (pangkat atas).
    Misalnya, '2' jadi '²', '-' jadi '⁻'.
    Ini dipakai untuk menampilkan toleransi error yang pakai notasi pangkat.
    """
    text = str(text_val) # Pastikan inputnya string
    superscript_map = { # Kamus pemetaan karakter biasa ke superscript
        "0": "⁰", "1": "¹", "2": "²", "3": "³", "4": "⁴",
        "5": "⁵", "6": "⁶", "7": "⁷", "8": "⁸", "9": "⁹",
        "-": "⁻", ".": "⋅" # Titik juga diubah jadi simbol superscript yang sesuai
    }
    # Ganti setiap karakter di 'text' dengan versi superscriptnya jika ada di kamus, kalau tidak, pakai karakter aslinya.
    return "".join(superscript_map.get(char, char) for char in text)

def format_float(value, precision=8):
    """Memformat angka float agar tampilannya lebih rapi.
    Menghilangkan angka nol yang tidak perlu di akhir desimal.
    Misal: 1.2300 jadi '1.23', 5.0 jadi '5'.
    Juga menangani kasus None, infinity, dan NaN (Not a Number).
    Precision defaultnya 8 angka di belakang koma.
    """
    if value is None: # Jika nilainya kosong
        return "-" # Tampilkan strip
    if isinstance(value, str) and value == "-": # Jika sudah strip
        return value # Kembalikan apa adanya

    try:
        f_value = float(value) # Coba ubah jadi float
        if math.isinf(f_value) or math.isnan(f_value): # Jika tak hingga atau bukan angka
            return str(f_value) # Tampilkan sebagai string (misal "inf")

        # Cek apakah angka ini sebenarnya integer (misal 2.000000001 akan dianggap 2)
        # Toleransi 1e-9 (0.000000001) dipakai untuk mengatasi ketidakakuratan floating point kecil.
        if abs(f_value - round(f_value)) < 1e-9:
            return str(int(round(f_value))) # Jika ya, bulatkan dan jadikan integer, lalu string

        # Format ke jumlah desimal (precision) yang diinginkan dulu
        formatted_str = f"{f_value:.{precision}f}"

        # Kemudian, hilangkan nol di belakang koma jika memang ada bagian desimal
        if '.' in formatted_str:
            integer_part, decimal_part = formatted_str.split('.', 1) # Pisah bagian integer dan desimal
            decimal_part = decimal_part.rstrip('0') # Hapus nol di akhir bagian desimal
            if not decimal_part: # Jika setelah dihapus nol, bagian desimalnya kosong (misal "1.")
                return integer_part # Kembalikan bagian integernya saja (jadi "1")
            return f"{integer_part}.{decimal_part}" # Gabungkan lagi
        else:
            # Ini seharusnya jarang terjadi kalau inputnya float dan sudah diformat dengan presisi
            return formatted_str
    except (ValueError, TypeError): # Jika gagal diubah jadi float atau ada tipe yang salah
        return str(value) # Kembalikan sebagai string apa adanya

def parse_equation_for_lambdify(equation_str):
    """Mengurai (parse) string persamaan matematika menjadi fungsi Python yang bisa dihitung nilainya.
    Contoh: string "x^2 + 2*x" akan jadi fungsi f(x) = x*x + 2*x.
    Menggunakan Sympy untuk parsing dan lambdify.
    """
    try:
        x = sympy.symbols('x') # Definisikan 'x' sebagai simbol matematika untuk Sympy
        equation_str_processed = equation_str.lower().strip() # Ubah ke huruf kecil dan hapus spasi di awal/akhir
        if not equation_str_processed: # Jika persamaannya kosong
            raise ValueError("Persamaan tidak boleh kosong.")

        # Transformasi standar untuk parser Sympy:
        # - implicit_multiplication_application: biar '2x' diartikan '2*x'
        # - convert_xor: biar '^' diartikan sebagai pangkat (bukan operator XOR bitwise)
        transformations = standard_transformations + (implicit_multiplication_application, convert_xor)

        # Kamus lokal untuk mendefinisikan fungsi dan konstanta yang diizinkan dalam persamaan
        local_dict_sympy = {
            'x': x, 'sin': sympy.sin, 'cos': sympy.cos, 'tan': sympy.tan,
            'exp': sympy.exp, 'log': sympy.log, 'log10': lambda arg: sympy.log(arg, 10), # log basis 10
            'sqrt': sympy.sqrt, 'abs': sympy.Abs, 'pi': sympy.pi, 'e': sympy.E, 'pow': sympy.Pow
        }
        # Proses parsing string persamaan menjadi ekspresi Sympy. 'evaluate=True' agar ekspresi disederhanakan jika memungkinkan.
        parsed_expr = parse_expr(equation_str_processed, local_dict=local_dict_sympy, transformations=transformations, evaluate=True)
        if parsed_expr is None: raise ValueError("Gagal mem-parsing ekspresi menjadi None.") # Jika parsing gagal total

        # Cek apakah ada variabel lain selain 'x' di persamaan
        free_symbols = parsed_expr.free_symbols # Dapatkan semua simbol bebas (variabel) dalam ekspresi
        if free_symbols and (free_symbols - {x}): # Jika ada simbol bebas, dan simbol itu bukan 'x'
            unknown_symbols = free_symbols - {x} # Cari simbol apa saja yang tidak dikenal
            raise ValueError(f"Ditemukan variabel yang tidak dikenal: {', '.join(map(str, unknown_symbols))}. Hanya 'x' yang diizinkan.")

        # Modul yang akan digunakan oleh 'lambdify' untuk evaluasi numerik.
        # Ini memberitahu lambdify untuk menggunakan fungsi dari 'math' atau 'numpy' saat menghitung.
        numerical_modules = [
            {'exp': math.exp, 'log': math.log, 'log10': math.log10,
             'sin': math.sin, 'cos': math.cos, 'tan': math.tan,
             'sqrt': math.sqrt, 'abs': abs, 'pi': math.pi, 'e': math.e, 'pow': pow}, "numpy"
        ]
        try:
            # Ubah ekspresi Sympy ('parsed_expr') menjadi fungsi Python biasa yang siap pakai.
            # Fungsi ini akan menerima satu argumen (nilai x) dan mengembalikan hasil perhitungan.
            func = sympy.lambdify(x, parsed_expr, modules=numerical_modules)
            try:
                _ = func(1.0) # Tes fungsi dengan nilai dummy (misal 1.0) untuk memastikan ia bekerja
            except TypeError as te: # Tangkap error jika ekspresi ternyata adalah konstanta (misal "5" atau "pi")
                if parsed_expr.is_constant(): # Jika memang konstanta
                    const_val = float(parsed_expr.evalf()) # Evaluasi nilai konstanta tersebut
                    func = lambda val: const_val # Buat fungsi lambda yang selalu mengembalikan nilai konstanta itu
                else: # Jika error lain, bukan karena konstanta
                    raise ValueError(f"Ekspresi '{equation_str}' tidak bisa diubah menjadi fungsi dari x. Detail: {te}")
            return func # Kembalikan fungsi yang sudah jadi
        except RuntimeError as rterr : # Error spesifik dari lambdify, misal fungsi tidak didukung
             raise ValueError(f"Error saat membuat fungsi numerik dari '{equation_str}'. Mungkin ada fungsi yang tidak didukung oleh lambdify. Detail: {rterr}")

    except (SyntaxError, TypeError, AttributeError, ValueError) as e: # Tangkap berbagai jenis error parsing/validasi
        error_detail = str(e)
        if isinstance(e, SyntaxError): error_detail = f"Kesalahan sintaks: {e.msg} (dekat '{e.text}')" # Pesan error lebih jelas untuk SyntaxError
        guidance = (f"Error parsing equation (for calculation): {error_detail}\n\n"
                    "Pastikan format benar. Cek tips di GUI.")
        raise ValueError(guidance) # Kirim error dengan pesan yang lebih informatif
    except Exception as e: # Tangkap error tak terduga lainnya
        raise ValueError(f"Error tak terduga saat parsing (for calculation): {str(e)}")

def get_latex_from_equation(equation_str):
    """Mengubah string persamaan matematika menjadi format LaTeX untuk ditampilkan di pratinjau.
    Mirip 'parse_equation_for_lambdify' tapi outputnya string LaTeX, bukan fungsi.
    """
    equation_str_processed = str(equation_str).lower().strip() # Standarisasi input
    if not equation_str_processed: # Jika kosong
        return "" # Kembalikan string kosong

    try:
        x = sympy.symbols('x') # Definisikan simbol x
        transformations = standard_transformations + (implicit_multiplication_application, convert_xor) # Transformasi yang sama
        local_dict_sympy = { # Kamus simbol dan fungsi Sympy
            'x': x, 'sin': sympy.sin, 'cos': sympy.cos, 'tan': sympy.tan,
            'exp': sympy.exp, 'log': sympy.log, 'log10': sympy.Function('log10'), # log10 didefinisikan sebagai Fungsi Sympy agar LaTeX-nya benar
            'sqrt': sympy.sqrt, 'abs': sympy.Abs, 'pi': sympy.pi, 'e': sympy.E, 'pow': sympy.Pow
        }
        # Parse persamaan. 'evaluate=False' penting di sini agar struktur asli persamaan (misal 2*x bukan 2x)
        # lebih terjaga untuk output LaTeX yang lebih natural.
        parsed_expr = parse_expr(equation_str_processed, local_dict=local_dict_sympy, transformations=transformations, evaluate=False)
        if parsed_expr is None: # Jika parsing gagal
             return r"\text{Error: Tidak dapat parsing}" # Kembalikan pesan error dalam format LaTeX

        # Opsi untuk sympy.latex:
        # - mul_symbol='dot': simbol perkalian jadi titik (·) bukan spasi.
        # - fold_short_frac=False: jangan lipat pecahan pendek.
        # - long_frac_ratio=2: rasio untuk menentukan pecahan panjang.
        return sympy.latex(parsed_expr, mul_symbol='dot', fold_short_frac=False, long_frac_ratio=2)
    except (SyntaxError, TypeError, AttributeError) as e: # Tangkap error parsing umum
        # Logika untuk memberikan feedback saat pengguna mengetik operator di akhir persamaan
        # Misal, user ketik "x^", pratinjau akan jadi "x^{\square}"
        if equation_str_processed.endswith(tuple(['^', '**', '*', '/', '+', '-'])): # Cek apakah diakhiri operator
            base_part, op_char = "", "" # Inisialisasi bagian dasar dan operatornya
            # Tentukan apa bagian dasar dan apa operatornya
            if equation_str_processed.endswith('^'): base_part, op_char = equation_str_processed[:-1], "^"
            elif equation_str_processed.endswith('**'): base_part, op_char = equation_str_processed[:-2], "**"
            elif equation_str_processed.endswith(tuple(['*', '/', '+', '-'])): base_part, op_char = equation_str_processed[:-1], equation_str_processed[-1]

            if base_part.strip(): # Jika ada bagian dasar sebelum operator (bukan cuma operator saja)
                try:
                    # Coba parse bagian dasarnya saja
                    base_expr_preview = parse_expr(base_part.strip(), local_dict=local_dict_sympy, transformations=transformations, evaluate=False)
                    if base_expr_preview:
                        if op_char in ["^", "**"]: return sympy.latex(base_expr_preview, mul_symbol='dot') + r"^{\square}" # Untuk pangkat, tambahkan placeholder pangkat
                        else: return sympy.latex(base_expr_preview, mul_symbol='dot') + sympy.latex(op_char, mode='plain') + r"\text{ ?}" # Operator lain, tambahkan placeholder operand kedua
                except: pass # Abaikan error di sini, akan fallback ke pesan umum
            return r"\text{Lanjutkan mengetik...}" # Jika hanya operator atau base_part kosong
        return r"\text{Input tidak valid}" # Pesan error LaTeX umum jika bukan kasus di atas
    except Exception: # Tangkap error tak terduga lainnya
        return r"\text{Error pratinjau}"

def bisection_method(equation_str, a_str, b_str, tol_str, max_iter_str="100"):
    """Fungsi inti yang menjalankan algoritma metode bagi dua.
    Menerima string persamaan, interval awal [a,b], toleransi, dan maks iterasi.
    Mengembalikan dictionary berisi akar, data iterasi, pesan, dll.
    """
    iteration_log_text = [] # List untuk menyimpan log teks setiap langkah iterasi
    value_precision = 8 # Presisi angka untuk nilai a, b, c, f(x) di log dan tabel
    error_precision = 10 # Presisi angka untuk nilai error

    tol = 0.0 # Inisialisasi nilai toleransi (akan diisi dari input)
    try:
        # 1. Parse persamaan string menjadi fungsi f(x) yang bisa dievaluasi
        f = parse_equation_for_lambdify(equation_str)

        # 2. Konversi input string a, b, toleransi, max_iter menjadi tipe numerik (float/int)
        a = float(a_str); b = float(b_str) # Ubah string a dan b ke float
        if a == b: return {'error': "Interval a dan b tidak boleh sama."} # Validasi a dan b
        if a > b: # Jika a > b, tukar nilainya agar a selalu lebih kecil dari b
            a, b = b, a
            iteration_log_text.append("Info: Nilai a dan b ditukar karena a > b.\n")

        try:
            # Evaluasi string toleransi dengan aman. Ini memungkinkan input seperti "10^-5" atau "0.1/2".
            tol_val_str_eval = tol_str.replace(" ", "") # Hapus spasi
            # Ganti format pangkat 'x^y' atau 'x^(y)' menjadi 'x**y' yang bisa dievaluasi Python
            tol_val_str_eval = re.sub(r'(\d+(?:\.\d+)?(?:[eE][-+]?\d+)?)\s*\^\s*\(?\s*(-?\d+(?:\.\d+)?)\s*\)?', r'\1**\2', tol_val_str_eval)
            tol_val_str_eval = re.sub(r'(\d+(?:\.\d+)?(?:[eE][-+]?\d+)?)\s*\^\s*(-?\d+(?:\.\d+)?)', r'\1**\2', tol_val_str_eval) # Versi tanpa kurung untuk eksponen

            # Hanya izinkan operasi matematika dasar (+, -, *, /, **) dan konstanta dari modul 'math' (e, pi)
            # Ini untuk keamanan, agar tidak sembarang kode Python bisa dieksekusi dari input toleransi.
            if any(op in tol_val_str_eval for op in ['**', '/', '*', '+', '-']):
                 tol = float(eval(tol_val_str_eval, {"__builtins__": None}, {"math": math, "e": math.e, "pi": math.pi}))
            else: # Jika hanya angka biasa
                 tol = float(tol_val_str_eval)

            if tol <= 0: return {'error': "Toleransi error (ε) harus lebih besar dari nol."} # Validasi toleransi
        except Exception as e_tol: # Jika ada error saat evaluasi string toleransi
            return {'error': f"Format toleransi tidak valid: '{tol_str}'.\nDetail: {str(e_tol)}"}

        max_iter = int(max_iter_str) # Ubah string max_iter ke integer
        if max_iter <=0: return {'error': "Maksimum iterasi harus lebih besar dari nol."} # Validasi max_iter
    except ValueError as e: return {'error': str(e)} # Error jika konversi tipe gagal (misal input bukan angka)
    except Exception as e: return {'error': f"Input tidak valid: {str(e)}."} # Error umum lainnya dari persiapan input

    # Format tampilan toleransi untuk log, bisa jadi pakai superscript jika inputnya pakai '^' atau '**'
    display_tol_for_log = format_float(tol, error_precision) # Tampilan default
    original_tol_input = tol_str.strip()
    # Cek apakah format toleransi input menggunakan ^ atau **
    match_caret = re.match(r"^\s*([\d\.]+|[eE]|[pP][iI])\s*\^\s*\(?\s*([-\d\.]+)\s*\)?\s*$", original_tol_input)
    match_star = re.match(r"^\s*([\d\.]+|[eE]|[pP][iI])\s*\*\*\s*\(?\s*([-\d\.]+)\s*\)?\s*$", original_tol_input)
    if match_caret: # Jika pakai '^'
        base, exp = match_caret.groups()
        display_tol_for_log = f"{base}{to_superscript(exp)} (dihitung sebagai: {format_float(tol, error_precision)})"
    elif match_star: # Jika pakai '**'
        base, exp = match_star.groups()
        display_tol_for_log = f"{base}{to_superscript(exp)} (dihitung sebagai: {format_float(tol, error_precision)})"

    # 3. Hitung f(a) dan f(b) awal
    try:
        f_a_initial, f_b_initial = f(a), f(b)
    except Exception as e_eval: # Tangkap error jika evaluasi f(a) atau f(b) gagal (misal pembagian dengan nol di persamaan)
        return {'error': f"Error saat menghitung f(x) pada interval awal: {str(e_eval)}.\nCek persamaan atau interval."}


    epsilon_zero_check = 1e-12 # Angka yang sangat kecil untuk perbandingan dengan nol (mengatasi isu presisi float)

    # 4. Cek kondisi awal metode biseksi
    #    a. Jika f(a) atau f(b) sudah sangat dekat dengan nol, berarti a atau b adalah akarnya.
    if abs(f_a_initial) < epsilon_zero_check:
        iteration_log_text.append(f"Data Awal:\n  f(a) = f({format_float(a, value_precision)}) = {format_float(f_a_initial, value_precision)} ≈ 0. Titik 'a' adalah akar.\n")
        return {'root': format_float(a, value_precision), 'iterations_data': [], 'message': f"Akar ditemukan pada x = {format_float(a, value_precision)} (f(a) ≈ 0).", 'final_absolute_error': 0.0, 'tolerance': tol, 'iteration_log_text': iteration_log_text}
    if abs(f_b_initial) < epsilon_zero_check:
        iteration_log_text.append(f"Data Awal:\n  f(b) = f({format_float(b, value_precision)}) = {format_float(f_b_initial, value_precision)} ≈ 0. Titik 'b' adalah akar.\n")
        return {'root': format_float(b, value_precision), 'iterations_data': [], 'message': f"Akar ditemukan pada x = {format_float(b, value_precision)} (f(b) ≈ 0).", 'final_absolute_error': 0.0, 'tolerance': tol, 'iteration_log_text': iteration_log_text}

    #    b. Syarat utama: f(a) dan f(b) harus berbeda tanda (f(a) * f(b) < 0)
    if f_a_initial * f_b_initial > 0:
        return {'error': f"f(a) & f(b) tidak beda tanda. f({format_float(a,value_precision)})={format_float(f_a_initial,value_precision)}, f({format_float(b,value_precision)})={format_float(f_b_initial,value_precision)}."}

    iterations_data = [] # List untuk menyimpan data per iterasi (untuk tabel)
    c_prev_iter = None   # c dari iterasi sebelumnya, untuk hitung error absolut. Awalnya None.

    # Log data awal sebelum iterasi dimulai
    iteration_log_text.append(f"Data Awal:\n  Persamaan f(x) = {equation_str}\n  Interval awal: [{format_float(a, value_precision)}, {format_float(b, value_precision)}]\n  Toleransi (ε): {display_tol_for_log}\n  f(a) = f({format_float(a, value_precision)}) = {format_float(f_a_initial, value_precision)}\n  f(b) = f({format_float(b, value_precision)}) = {format_float(f_b_initial, value_precision)}\n  Kondisi awal terpenuhi (f(a) * f(b) < 0).\n")

    c = a # Inisialisasi c (misal dengan a), dipakai jika max_iter = 0 atau sangat kecil.

    # 5. Loop Iterasi Utama
    for n in range(1, max_iter + 1): # Loop dari 1 sampai max_iter
        # Bagian log untuk header setiap iterasi
        log_parts = [f"\n\n\n====== Iterasi ke-{n} ======"] # Ini akan diberi gaya khusus di GUI
        log_parts.append(f"  Interval saat ini [{format_float(a, value_precision)},{format_float(b, value_precision)}]: a = {format_float(a, value_precision)}, b = {format_float(b, value_precision)}")
        try:
            f_a_curr, f_b_curr = f(a), f(b) # Hitung f(a) dan f(b) untuk interval saat ini
        except Exception as e_eval_iter: # Tangkap error jika evaluasi f(x) gagal di tengah iterasi
            iteration_log_text.append("\n".join(log_parts)) # Tambahkan log yang sudah ada
            iteration_log_text.append(f"  Error saat menghitung f(x) di iterasi {n}: {str(e_eval_iter)}")
            return {'error': f"Error evaluasi f(x) pada iterasi {n}: {str(e_eval_iter)}", 'iteration_log_text': iteration_log_text, 'iterations_data':iterations_data}

        log_parts.extend([f"  f(a) = {format_float(f_a_curr, value_precision)}", f"  f(b) = {format_float(f_b_curr, value_precision)}"])

        # Kondisi berhenti tambahan: jika interval [a,b] sudah sangat kecil
        if abs(b-a) < epsilon_zero_check:
            c = (a+b)/2 # Aproksimasi c sebagai tengah interval
            abs_err = abs(c - c_prev_iter) if c_prev_iter is not None else 0.0 # Hitung error absolut jika memungkinkan
            log_parts.append(f"  Interval [a,b] sudah sangat kecil ({format_float(abs(b-a), error_precision)}). Aproksimasi c = {format_float(c, value_precision)}. Hentikan.")
            # Siapkan data untuk tabel ringkasan
            tbl_info = {"n":n,"a":format_float(a,value_precision),"f(a)":format_float(f_a_curr,value_precision),"b":format_float(b,value_precision),"f(b)":format_float(f_b_curr,value_precision),"c":format_float(c,value_precision),"f(c)":format_float(f(c),value_precision),"Abs_Error":format_float(abs_err,error_precision),"Rel_Error_Percent":"-","Update":"Interval sgt kecil"}
            iterations_data.append(tbl_info)
            iteration_log_text.append("\n".join(log_parts))
            # Kembalikan hasil
            return {'root':format_float(c,value_precision),'iterations_data':iterations_data,'message':f"Interval sgt kecil. Aproksimasi x={format_float(c,value_precision)} ({n} iter).",'final_absolute_error':abs_err,'tolerance':tol,'iteration_log_text':iteration_log_text}

        #   a. Hitung titik tengah c = (a+b)/2
        c_calc = (a + b) / 2
        #   Simulasi tampilan c sebagai pecahan di log untuk kejelasan
        val_a_str,val_b_str = format_float(a,value_precision),format_float(b,value_precision)
        sum_ab = a+b; val_sum_ab_str = format_float(sum_ab,value_precision); val_c_str = format_float(c_calc,value_precision)
        num_s1,den_s = f"{val_a_str} + {val_b_str}","2" # Pembilang dan penyebut sebagai string
        max_len_s1,max_len_s2 = max(len(num_s1),len(den_s)),max(len(val_sum_ab_str),len(den_s)) # Untuk alignment
        c_lbl = "c" # Bisa juga c_n jika ingin c dengan indeks iterasi
        log_parts.extend([f"  Perhitungan {c_lbl}:",f"    {c_lbl} =  {num_s1.center(max_len_s1)}",f"          {'-'*max_len_s1}",f"          {den_s.center(max_len_s1)}",f"    {c_lbl} =  {val_sum_ab_str.center(max_len_s2)}  =  {val_c_str}",f"          {'-'*max_len_s2}",f"          {den_s.center(max_len_s2)}",""])
        c = c_calc # Simpan nilai c yang dihitung

        # Kondisi berhenti tambahan: jika c sama persis dengan a atau b (karena batas presisi float)
        # Ini mencegah loop tak hingga jika interval tidak bisa dibagi lebih kecil lagi.
        if c == a or c == b:
            abs_err = abs(c - c_prev_iter) if c_prev_iter is not None else 0.0
            log_parts.append(f"  Titik tengah c ({format_float(c,value_precision)}) sama dengan a atau b. Batas presisi tercapai.")
            tbl_info = {"n":n,"a":format_float(a,value_precision),"f(a)":format_float(f_a_curr,value_precision),"b":format_float(b,value_precision),"f(b)":format_float(f_b_curr,value_precision),"c":format_float(c,value_precision),"f(c)":format_float(f(c),value_precision),"Abs_Error":format_float(abs_err,error_precision),"Rel_Error_Percent":"-","Update":"Presisi tercapai"}
            iterations_data.append(tbl_info)
            iteration_log_text.append("\n".join(log_parts))
            return {'root':format_float(c,value_precision),'iterations_data':iterations_data,'message':f"Batas presisi. Aproksimasi x={format_float(c,value_precision)} ({n} iter).",'final_absolute_error':abs_err,'tolerance':tol,'iteration_log_text':iteration_log_text}

        #   b. Hitung f(c)
        try:
            f_c = f(c)
        except Exception as e_eval_fc: # Tangkap error jika evaluasi f(c) gagal
            iteration_log_text.append("\n".join(log_parts))
            iteration_log_text.append(f"  Error saat menghitung f(c) di iterasi {n}: {str(e_eval_fc)}")
            return {'error': f"Error evaluasi f(c) pada iterasi {n}: {str(e_eval_fc)}", 'iteration_log_text': iteration_log_text, 'iterations_data':iterations_data}
        log_parts.append(f"  f({c_lbl}) = f({format_float(c, value_precision)}) = {format_float(f_c, value_precision)}")

        abs_err, rel_err_pct = None, None # Inisialisasi variabel error

        #   c. Hitung error (jika bukan iterasi pertama, karena butuh c_sebelumnya)
        if c_prev_iter is not None:
            abs_err = abs(c - c_prev_iter) # Error Absolut: |c_sekarang - c_sebelumnya|
            log_parts.append(f"  Error Absolut (e) = |{format_float(c,value_precision)} - {format_float(c_prev_iter,value_precision)}| = {format_float(abs_err, error_precision)}")
            if abs(c) > epsilon_zero_check: # Hindari pembagian dengan nol untuk error relatif
                rel_err_pct = abs(abs_err/c)*100 # Error Relatif Persen
                log_parts.append(f"  Error Relatif (%) = (|{format_float(abs_err,error_precision)}| / |{format_float(c,value_precision)}|) * 100% = {format_float(rel_err_pct,2)}%")
            else: # Jika c sangat dekat dengan nol
                rel_err_pct = float('inf') # Anggap error relatif tak hingga jika c = 0
                log_parts.append("  Error Relatif (%) = N/A (c ≈ 0)")
        else: # Iterasi pertama
            log_parts.append("  Error belum dihitung (iterasi pertama).")

        # Siapkan data untuk dimasukkan ke tabel ringkasan
        tbl_info = {"n":n,"a":format_float(a,value_precision),"f(a)":format_float(f_a_curr,value_precision),"b":format_float(b,value_precision),"f(b)":format_float(f_b_curr,value_precision),"c":format_float(c,value_precision),"f(c)":format_float(f_c,value_precision),"Abs_Error":format_float(abs_err,error_precision) if abs_err is not None else "-","Rel_Error_Percent":f"{format_float(rel_err_pct,2)}%" if rel_err_pct is not None and rel_err_pct!=float('inf') else ("-" if abs_err is None else "N/A")}

        upd_txt = "" # Teks untuk kolom "Update" di tabel (misal "a = c" atau "b = c")

        #   d. Cek kondisi berhenti: Jika f(c) sangat dekat dengan nol, maka c adalah akar.
        if abs(f_c) < epsilon_zero_check:
            upd_txt = "Akar ditemukan (f(c) ≈ 0)!"
            log_parts.append(f"  Status: {upd_txt} (f(c) = {format_float(f_c, error_precision)})") # Tampilkan f(c) dengan presisi lebih tinggi
            tbl_info["Update"] = upd_txt
            iterations_data.append(tbl_info)
            iteration_log_text.append("\n".join(log_parts))
            return {'root':format_float(c,value_precision),'iterations_data':iterations_data,'message':f"Akar x={format_float(c,value_precision)} ({n} iter, f(c)≈0).",'final_absolute_error':abs_err if abs_err is not None else 0.0,'tolerance':tol,'iteration_log_text':iteration_log_text}

        #   e. Update interval [a,b] untuk iterasi selanjutnya
        prod_fa_fc, prod_fc_fb = f_a_curr * f_c, f_c * f_b_curr # f(a)*f(c) dan f(c)*f(b)
        if prod_fa_fc < 0: # Jika f(a) dan f(c) beda tanda, akar ada di [a,c]
            b_new,a_new,upd_txt = c,a,"b = c" # b baru jadi c, a tetap
        elif prod_fc_fb < 0: # Jika f(c) dan f(b) beda tanda, akar ada di [c,b]
            a_new,b_new,upd_txt = c,b,"a = c" # a baru jadi c, b tetap
        # Kasus pengaman jika f(a) atau f(b) sudah sangat dekat nol tapi produknya >=0 (karena f(c) juga dekat nol)
        elif abs(f_a_curr)<epsilon_zero_check and prod_fc_fb >=0:
            b_new,a_new,upd_txt = c,a,"b = c (f(a)≈0)"
        elif abs(f_b_curr)<epsilon_zero_check and prod_fa_fc >=0:
            a_new,b_new,upd_txt = c,b,"a = c (f(b)≈0)"
        else: # Seharusnya ini tidak terjadi jika kondisi f(a)*f(b) < 0 selalu dijaga
            upd_txt = "Err: Interval?"
            log_parts.append(f"  Peringatan: Problem interval. f(a)={format_float(f_a_curr,value_precision)}, f(b)={format_float(f_b_curr,value_precision)}, f(c)={format_float(f_c,value_precision)}")
            tbl_info["Update"] = upd_txt
            iterations_data.append(tbl_info)
            iteration_log_text.append("\n".join(log_parts))
            # Kembalikan error jika ada masalah dengan update interval (sangat jarang terjadi)
            return {'error':f"Problem interval iter {n}. f(a)f(c)={prod_fa_fc:.2e}, f(c)f(b)={prod_fc_fb:.2e}",'iteration_log_text':iteration_log_text}

        log_parts.append(f"  Update: {upd_txt}. Interval baru: [{format_float(a_new,value_precision)}, {format_float(b_new,value_precision)}]")
        a,b = a_new,b_new # Perbarui nilai a dan b untuk iterasi berikutnya
        tbl_info["Update"] = upd_txt
        iterations_data.append(tbl_info) # Simpan data iterasi ini
        iteration_log_text.append("\n".join(log_parts)) # Tambahkan semua log dari iterasi ini

        c_prev_iter_for_next = c # Simpan c saat ini untuk perhitungan error di iterasi berikutnya

        #   f. Cek kondisi berhenti: Jika error absolut < toleransi (ε)
        if abs_err is not None and abs_err < tol:
            iteration_log_text.append(f"\n\n\nKonvergensi: Error Absolut ({format_float(abs_err,error_precision)}) < Toleransi Error ({format_float(tol,error_precision)})")
            return {'root':format_float(c,value_precision),'iterations_data':iterations_data,'message':f"Konvergen x={format_float(c,value_precision)} (Iterasi Ke-{n}).",'final_absolute_error':abs_err,'tolerance':tol,'iteration_log_text':iteration_log_text}

        c_prev_iter = c_prev_iter_for_next # Update c_prev_iter untuk iterasi selanjutnya

    # 6. Jika loop selesai karena max_iter tercapai (bukan karena kondisi berhenti lain)
    final_err = abs_err if abs_err is not None else 0.0 # Error terakhir yang dihitung
    iteration_log_text.append(f"\nPeringatan:\n  Maksimum iterasi ({max_iter}) tercapai.")
    return {'root':format_float(c,value_precision),'iterations_data':iterations_data,'message':f"Maks iter ({max_iter}). Aproksimasi x={format_float(c,value_precision)}.",'final_absolute_error':final_err,'tolerance':tol,'iteration_log_text':iteration_log_text}

# --- Frontend GUI --- (Bagian kode untuk tampilan antarmuka pengguna)
class BisectionCalculatorApp(ctk.CTk): # Kelas utama aplikasi, mewarisi dari CTk (CustomTkinter)
    def __init__(self): # Konstruktor, dieksekusi saat objek aplikasi dibuat
        super().__init__() # Panggil konstruktor kelas induk (CTk)
        self.title("Bisection Method Calculator - New Palette"); self.geometry("1350x900") # Judul window dan ukuran awal

        # --- Color Palette --- (Definisi warna-warna yang akan dipakai di UI)
        self.clr_dark_purple = "#210440"
        self.clr_light_peach_base = "#FDB095"
        self.clr_dusty_rose = "#E5958E"
        self.clr_golden_yellow = "#FFBA00"
        self.clr_white = "#FFFFFF"

        # --- Derived UI Colors --- (Warna UI yang diturunkan dari palet dasar)
        self.app_bg_color = "#FEFBF9"       # Latar belakang aplikasi utama (peach sangat terang)
        self.text_color = self.clr_dark_purple # Warna teks umum
        self.entry_fg_color = self.clr_white   # Warna foreground (isian) untuk kolom input
        self.entry_border_color = self.clr_light_peach_base # Warna border kolom input
        self.entry_text_color = self.clr_dark_purple # Warna teks di dalam kolom input
        self.button_fg_color = self.clr_dark_purple # Warna foreground tombol
        self.button_text_color = self.clr_white     # Warna teks tombol
        self.button_hover_color = "#3A1F78"       # Warna tombol saat mouse hover (ungu lebih terang)
        self.accent_color_result = self.clr_dusty_rose # Warna aksen untuk pesan hasil
        self.log_fg_color = self.clr_white         # Warna foreground (background) area log
        self.log_text_color = self.clr_dark_purple # Warna teks di area log
        self.preview_fg_color = "#FDECDC"       # Warna foreground (background) area pratinjau LaTeX

        # --- Treeview Specific Colors --- (Warna khusus untuk tabel Treeview)
        self.tree_heading_bg = self.clr_dark_purple # Background header kolom tabel
        self.tree_heading_fg = self.clr_white       # Teks header kolom tabel
        self.tree_row_bg = self.clr_white           # Background baris data tabel
        self.tree_row_fg = self.clr_dark_purple     # Teks baris data tabel
        self.tree_selected_bg = self.clr_golden_yellow # Background baris yang dipilih
        self.tree_selected_fg = self.clr_dark_purple   # Teks baris yang dipilih

        # --- Font Configuration --- (Pengaturan jenis dan ukuran font)
        self.font_general_size = 11 # Ukuran font umum
        self.font_log_family = "Consolas" # Font utama untuk log (monospace, agar rapi)
        self.font_log_size = 13
        self.font_log_fallback_family = "Courier New" # Font alternatif jika Consolas tidak ada

        # Cek ketersediaan font Consolas. Jika tidak ada, pakai Courier New.
        try:
            tkfont.Font(family=self.font_log_family, size=self.font_log_size).actual() # Coba buat font
            self.actual_log_font_family = self.font_log_family # Jika berhasil, pakai Consolas
        except tkfont.tkinter.TclError: # Error spesifik jika font tidak ditemukan
            self.actual_log_font_family = self.font_log_fallback_family # Pakai fallback
        except Exception: # Fallback umum untuk error lain
             self.actual_log_font_family = self.font_log_fallback_family

        # Tuple font untuk mempermudah penggunaan di widget
        self.font_log_tuple = (self.actual_log_font_family, self.font_log_size)
        self.font_table_row_tuple = ("Segoe UI", 10) # Font baris tabel
        self.font_table_heading_tuple = ("Segoe UI", 11, "bold") # Font header tabel
        self.font_label_tuple = ("Segoe UI", self.font_general_size) # Font label biasa
        self.font_button_tuple = ("Segoe UI", self.font_general_size, "bold") # Font tombol
        self.font_entry_tuple = ("Segoe UI", self.font_general_size) # Font kolom input
        self.font_result_label_tuple = ("Segoe UI", 13, "bold") # Font label hasil utama
        self.font_convergence_info_tuple = ("Segoe UI", 10) # Font info konvergensi
        self.font_instruction_tuple = ("Segoe UI", 9) # Font teks instruksi

        # Konfigurasi warna foreground untuk tag 'iter_head' di log textbox
        # Tag ini akan dipakai untuk mewarnai header iterasi (misal "====== Iterasi ke-1 ======")
        self.tag_iter_head_fg_config = self.clr_dark_purple # Warna teks header iterasi di log

        ctk.set_appearance_mode("Light") # Set tema aplikasi ke mode terang
        self.configure(fg_color=self.app_bg_color) # Atur warna latar belakang utama aplikasi

        self.preview_canvas_widget = None # Variabel untuk menyimpan widget kanvas pratinjau Matplotlib

        # --- Input Frame --- (Frame/wadah untuk semua elemen input)
        self.input_frame = ctk.CTkFrame(self, fg_color="transparent") # Buat frame, fg_color="transparent" agar menyatu dengan background app
        self.input_frame.pack(pady=10, padx=20, fill="x") # Tempatkan frame di window (pack layout manager)

        # Label dan Entry untuk Persamaan f(x)
        ctk.CTkLabel(self.input_frame, text="Persamaan f(x) = 0:", text_color=self.text_color, font=self.font_label_tuple).grid(row=0, column=0, padx=5, pady=5, sticky="nw") # Label
        self.equation_entry = ctk.CTkEntry(self.input_frame, width=350, placeholder_text="Contoh: x^3 + 4x^2 - 10", # Kolom input
                                           fg_color=self.entry_fg_color, text_color=self.entry_text_color,
                                           border_color=self.entry_border_color, font=self.font_entry_tuple)
        self.equation_entry.grid(row=0, column=1, padx=5, pady=5, sticky="ew") # Tempatkan dengan grid layout manager
        self.equation_entry.insert(0, "x^3 + 4*x^2 - 10") # Isi dengan contoh persamaan awal

        # Tombol untuk Refresh Pratinjau Persamaan
        self.refresh_preview_button = ctk.CTkButton(self.input_frame, text="🔄 Pratinjau", width=120,
                                                    command=self.update_equation_preview, # Fungsi yang dipanggil saat diklik
                                                    fg_color=self.button_fg_color, hover_color=self.button_hover_color,
                                                    text_color=self.button_text_color, font=self.font_button_tuple)
        self.refresh_preview_button.grid(row=0, column=2, padx=(10,0), pady=5, sticky="w")

        # Area Pratinjau Persamaan (menggunakan Matplotlib)
        ctk.CTkLabel(self.input_frame, text="Pratinjau Persamaan:", text_color=self.text_color, font=self.font_label_tuple).grid(row=1, column=0, padx=5, pady=(5,0), sticky="nw")
        self.preview_frame = ctk.CTkFrame(self.input_frame, height=60, fg_color=self.preview_fg_color, corner_radius=5) # Frame untuk pratinjau
        self.preview_frame.grid(row=1, column=1, columnspan=2, padx=5, pady=5, sticky="ew")
        self.preview_frame.grid_propagate(False) # Agar ukuran frame tidak berubah mengikuti isinya (fixed height)
        self.initial_preview_text_label = ctk.CTkLabel(self.preview_frame, text="Klik '🔄 Pratinjau' untuk melihat", # Teks awal di area pratinjau
                                                       text_color=self.text_color, anchor="center", font=self.font_label_tuple)
        self.initial_preview_text_label.pack(expand=True, fill="both", padx=5, pady=5) # Tampilkan teks awal

        input_row_start = 2 # Baris awal untuk input a, b, dst. (agar mudah jika mau tambah elemen di atasnya)
        # Label dan Entry untuk Interval [a, b]
        ctk.CTkLabel(self.input_frame, text="Interval [a, b]:", text_color=self.text_color, font=self.font_label_tuple).grid(row=input_row_start, column=0, padx=5, pady=5, sticky="w")
        self.a_entry = ctk.CTkEntry(self.input_frame, width=120, fg_color=self.entry_fg_color, text_color=self.entry_text_color, border_color=self.entry_border_color, font=self.font_entry_tuple)
        self.a_entry.grid(row=input_row_start, column=1, padx=5, pady=5, sticky="w"); self.a_entry.insert(0, "1") # Input a, contoh "1"
        self.b_entry = ctk.CTkEntry(self.input_frame, width=120, fg_color=self.entry_fg_color, text_color=self.entry_text_color, border_color=self.entry_border_color, font=self.font_entry_tuple)
        self.b_entry.grid(row=input_row_start, column=1, padx=(130,5), pady=5, sticky="w"); self.b_entry.insert(0, "1.5") # Input b, contoh "1.5" (padx=(130,5) memberi jarak dari a_entry)

        # Label dan Entry untuk Toleransi Error (ε)
        ctk.CTkLabel(self.input_frame, text="Toleransi Error (ε):", text_color=self.text_color, font=self.font_label_tuple).grid(row=input_row_start+1, column=0, padx=5, pady=5, sticky="w")
        self.tol_entry = ctk.CTkEntry(self.input_frame, width=180, fg_color=self.entry_fg_color, text_color=self.entry_text_color, border_color=self.entry_border_color, font=self.font_entry_tuple)
        self.tol_entry.grid(row=input_row_start+1, column=1, padx=5, pady=5, sticky="w"); self.tol_entry.insert(0, "0.00001") # Contoh "0.00001"

        # Label dan Entry untuk Maksimum Iterasi
        ctk.CTkLabel(self.input_frame, text="Maks Iterasi:", text_color=self.text_color, font=self.font_label_tuple).grid(row=input_row_start+2, column=0, padx=5, pady=5, sticky="w")
        self.max_iter_entry = ctk.CTkEntry(self.input_frame, width=180, fg_color=self.entry_fg_color, text_color=self.entry_text_color, border_color=self.entry_border_color, font=self.font_entry_tuple)
        self.max_iter_entry.grid(row=input_row_start+2, column=1, padx=5, pady=5, sticky="w"); self.max_iter_entry.insert(0, "100") # Contoh "100"

        # Teks Instruksi Format Persamaan
        instruction_text = ("Format Persamaan:\n- 'x' sebagai variabel.\n- Perkalian implisit: '4x', 'x(x+1)'.\n- Pangkat: 'x^3' atau 'x**3'.\n- Fungsi: sin,cos,tan,exp,log(ln),log10,sqrt,abs,pow.\n- Konstanta: pi, e.")
        ctk.CTkLabel(self.input_frame, text=instruction_text, text_color=self.text_color, justify="left", wraplength=300, font=self.font_instruction_tuple).grid(row=0, column=3, rowspan=input_row_start+3, padx=(20,5), pady=5, sticky="nw") # Teks di sisi kanan input

        # Tombol Hitung Akar
        self.calculate_button = ctk.CTkButton(self.input_frame, text="Hitung Akar", command=self.calculate_root, # Fungsi calculate_root dipanggil saat diklik
                                              fg_color=self.button_fg_color, hover_color=self.button_hover_color,
                                              text_color=self.button_text_color, font=self.font_button_tuple, height=35)
        self.calculate_button.grid(row=input_row_start+3, column=0, columnspan=3, pady=(15,10)) # Tempatkan di bawah input, agak lebar
        self.input_frame.columnconfigure(1, weight=1) # Kolom kedua (tempat entry) di input_frame bisa expand jika window di-resize

        # --- Output Notebook (Tabs) --- (Area output dengan beberapa tab)
        # Konfigurasi warna untuk CTkTabview
        self.output_notebook = ctk.CTkTabview(self, height=350, # Buat widget Tabview
                                             segmented_button_fg_color=self.clr_dark_purple, # Warna tombol tab (yang tidak aktif)
                                             segmented_button_selected_color=self.clr_golden_yellow, # Warna tab yang sedang dipilih
                                             segmented_button_selected_hover_color=self.clr_golden_yellow, # Warna hover tab yang dipilih
                                             segmented_button_unselected_color=self.app_bg_color, # Background tab yang tidak dipilih
                                             segmented_button_unselected_hover_color=self.preview_fg_color, # Hover tab yang tidak dipilih
                                             text_color=self.text_color, # Warna teks judul tab
                                             text_color_disabled=self.clr_light_peach_base # Warna teks tab jika disabled
                                             )
        self.output_notebook.pack(pady=10, padx=20, fill="both", expand=True) # Tempatkan Tabview, fill="both" dan expand=True agar mengisi sisa ruang
        self.output_notebook.add("Detail Perhitungan Iterasi") # Tambah tab pertama
        self.output_notebook.add("Tabel Ringkasan Iterasi")   # Tambah tab kedua
        self.output_notebook.set("Detail Perhitungan Iterasi") # Set tab pertama sebagai default yang aktif

        # --- Tab Log Iterasi Detail ---
        log_frame = self.output_notebook.tab("Detail Perhitungan Iterasi") # Dapatkan frame dari tab pertama
        self.iteration_log_textbox = ctk.CTkTextbox(log_frame, wrap="none", font=self.font_log_tuple, # Textbox untuk log, wrap="none" agar ada scroll horizontal
                                                    fg_color=self.log_fg_color, text_color=self.log_text_color,
                                                    border_width=1, border_color=self.entry_border_color)
        self.iteration_log_textbox.pack(fill="both", expand=True, padx=2, pady=2) # Tempatkan textbox
        # Konfigurasi tag 'iter_head'. Tag ini akan digunakan untuk memberi style pada bagian tertentu dari teks di textbox.
        # Di sini, hanya warna foreground (teks) yang diubah untuk 'iter_head'.
        self.iteration_log_textbox.tag_config("iter_head", foreground=self.tag_iter_head_fg_config)
        self.iteration_log_textbox.configure(state="disabled") # Awalnya, textbox tidak bisa diedit user


        # --- Tab Tabel Ringkasan Iterasi ---
        table_frame = self.output_notebook.tab("Tabel Ringkasan Iterasi") # Dapatkan frame dari tab kedua
        # Label untuk menampilkan pesan hasil utama (misal "Akar ditemukan pada x = ...")
        self.result_label = ctk.CTkLabel(table_frame, text="", text_color=self.accent_color_result, font=self.font_result_label_tuple, wraplength=1000, justify="left")
        self.result_label.pack(pady=(10,5), anchor="w", padx=5) # anchor="w" (west) agar rata kiri
        # Label untuk menampilkan info konvergensi (error final vs toleransi)
        self.convergence_info_label = ctk.CTkLabel(table_frame, text="", text_color=self.text_color, font=self.font_convergence_info_tuple, wraplength=1000, justify="left")
        self.convergence_info_label.pack(pady=5, anchor="w", padx=5)

        # Definisi kolom-kolom untuk tabel (Treeview)
        columns = ("Iterasi", "a", "f(a)", "b", "f(b)", "c", "f(c)", "Update", "Error Absolut", "Error Relatif(%)")
        # Buat widget Treeview dari tkinter.ttk. "show='headings'" berarti hanya header kolom yang tampil, bukan kolom dummy pertama.
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings", style="Custom.Treeview")

        # Konfigurasi style untuk Treeview (ttk). Style ini penting agar Treeview cocok dengan tema CustomTkinter.
        style_tree = ttk.Style()
        style_tree.theme_use("clam") # Tema 'clam' dipilih karena lebih fleksibel untuk dikustomisasi warnanya.
        # Style untuk header kolom
        style_tree.configure("Custom.Treeview.Heading",
                             font=self.font_table_heading_tuple,
                             background=self.tree_heading_bg, # Warna background header
                             foreground=self.tree_heading_fg, # Warna teks header
                             padding=(5,5), anchor="center") # Padding dan alignment teks header
        # Style untuk baris data di Treeview
        style_tree.configure("Custom.Treeview",
                             background=self.tree_row_bg,       # Warna background baris
                             foreground=self.tree_row_fg,       # Warna teks baris
                             fieldbackground=self.tree_row_bg,  # Warna background sel data
                             rowheight=28,                      # Tinggi baris (sesuaikan agar nyaman dibaca)
                             font=self.font_table_row_tuple)
        # Style untuk baris yang dipilih (selected item)
        style_tree.map('Custom.Treeview',
                       background=[('selected', self.tree_selected_bg)], # Background saat dipilih
                       foreground=[('selected', self.tree_selected_fg)])  # Teks saat dipilih

        # Atur lebar default untuk setiap kolom dan teks headernya
        col_widths = [40, 95, 95, 95, 95, 115, 115, 95, 115, 100] # Lebar dalam pixel
        for col, wd in zip(columns, col_widths):
            self.tree.heading(col, text=col, anchor="center") # Set teks header dan alignmentnya ke tengah
            self.tree.column(col, width=wd, anchor="center", minwidth=40) # Set lebar kolom dan alignment data ke tengah
        self.tree.pack(fill="both", expand=True, pady=(5,0), padx=5) # Tempatkan Treeview

        # Scrollbar untuk Treeview (vertikal dan horizontal) dengan warna kustom
        tree_scr_y = ctk.CTkScrollbar(self.tree, command=self.tree.yview, button_color=self.button_fg_color, button_hover_color=self.button_hover_color)
        tree_scr_y.pack(side="right", fill="y") # Scrollbar vertikal di kanan
        tree_scr_x = ctk.CTkScrollbar(self.tree, command=self.tree.xview, orientation="horizontal", button_color=self.button_fg_color, button_hover_color=self.button_hover_color)
        tree_scr_x.pack(side="bottom", fill="x") # Scrollbar horizontal di bawah
        # Hubungkan scrollbar dengan Treeview
        self.tree.configure(yscrollcommand=tree_scr_y.set, xscrollcommand=tree_scr_x.set)

    def update_equation_preview(self):
        """Fungsi untuk menampilkan pratinjau persamaan matematika menggunakan Matplotlib dan LaTeX."""
        # Hapus pratinjau lama jika ada (widget kanvas Matplotlib)
        if self.preview_canvas_widget:
            self.preview_canvas_widget.destroy(); self.preview_canvas_widget = None
        # Hapus juga teks awal "Klik '🔄 Pratinjau'..." jika masih ada
        if hasattr(self, 'initial_preview_text_label') and self.initial_preview_text_label.winfo_exists():
            self.initial_preview_text_label.pack_forget() # Sembunyikan/hapus dari layout

        eq_str = self.equation_entry.get() # Ambil string persamaan dari kolom input
        if not eq_str.strip(): # Jika inputnya kosong (atau hanya spasi)
            # Tampilkan lagi teks default jika input kosong
            self.initial_preview_text_label = ctk.CTkLabel(self.preview_frame, text="Klik '🔄 Pratinjau' untuk melihat",
                                                           text_color=self.text_color, anchor="center", font=self.font_label_tuple)
            self.initial_preview_text_label.pack(expand=True, fill="both", padx=5, pady=5)
            return # Selesai, tidak ada yang dipratinjau

        try:
            # 1. Dapatkan string LaTeX dari persamaan
            latex_str = get_latex_from_equation(eq_str)

            # 2. Setup Figure dan Axes Matplotlib untuk merender LaTeX
            fig = Figure(figsize=(6, 0.6), dpi=100, facecolor=self.preview_fg_color) # Ukuran figure, dpi, dan warna background
            ax = fig.add_subplot(111) # Tambah subplot (area gambar)
            ax.clear() # Bersihkan subplot (penting jika di-refresh)

            text_color_preview = self.text_color # Warna teks default untuk pratinjau
            font_size_preview = 12 # Ukuran font default untuk pratinjau

            # Tentukan teks yang akan dirender dan warnanya, berdasarkan hasil parsing LaTeX
            if not latex_str: # Jika string LaTeX kosong (error parsing yang tidak menghasilkan apa-apa)
                text_to_render, text_color_preview, font_size_preview = r"$\text{Input tidak valid untuk pratinjau.}$", self.clr_golden_yellow, 9
            elif latex_str.strip().startswith(r"\text{"): # Jika hasil parsing adalah teks error/info dari get_latex_from_equation (misal "\text{Lanjutkan mengetik...}")
                text_to_render = "$" + latex_str + "$" # Bungkus dengan $ agar dirender sebagai math text
                # Ubah warna jika itu pesan error atau input tidak valid
                text_color_preview = self.clr_dusty_rose if "Error" in latex_str or "valid" in latex_str else self.clr_golden_yellow
                font_size_preview = 9 # Perkecil font untuk pesan error/info
            else: # Jika LaTeX valid
                text_to_render = f"${latex_str}$" # Bungkus dengan $ agar dirender sebagai LaTeX math mode

            # 3. Render teks LaTeX ke subplot Matplotlib
            ax.text(0.5, 0.5, text_to_render, fontsize=font_size_preview, va='center', ha='center', color=text_color_preview, wrap=True)
            ax.axis('off') # Matikan sumbu (axis) agar tidak ada garis-garis koordinat
            fig.tight_layout(pad=0.05) # Atur layout agar pas dan tidak terpotong

            # 4. Tampilkan Figure Matplotlib di Tkinter menggunakan FigureCanvasTkAgg
            canvas = FigureCanvasTkAgg(fig, master=self.preview_frame) # Buat kanvas Tkinter dari figure Matplotlib
            self.preview_canvas_widget = canvas.get_tk_widget() # Dapatkan widget Tkinter-nya
            self.preview_canvas_widget.pack(side=ctk.TOP, fill=ctk.BOTH, expand=True, padx=2, pady=2) # Tempatkan widget kanvas di frame pratinjau
            canvas.draw() # Gambar kanvasnya
        except Exception as e: # Tangkap error umum yang mungkin terjadi saat membuat pratinjau
            if self.preview_canvas_widget: self.preview_canvas_widget.destroy(); self.preview_canvas_widget = None # Hapus kanvas jika ada error
            # Tampilkan pesan error di area pratinjau
            self.initial_preview_text_label = ctk.CTkLabel(self.preview_frame, text=f"Error Pratinjau Umum: {str(e)[:50]}", # Tampilkan sebagian pesan error
                                                           text_color=self.clr_dusty_rose, font=("Segoe UI",9), anchor="center")
            self.initial_preview_text_label.pack(expand=True, fill="both", padx=5, pady=5)

    def calculate_root(self):
        """Fungsi utama yang dipanggil saat tombol 'Hitung Akar' ditekan.
        Mengambil input, memanggil bisection_method, dan menampilkan hasilnya di GUI.
        """
        # Bersihkan output dari perhitungan sebelumnya
        for i in self.tree.get_children(): # Hapus semua baris data di tabel Treeview
            self.tree.delete(i)
        self.result_label.configure(text="") # Kosongkan label hasil
        self.convergence_info_label.configure(text="") # Kosongkan label info konvergensi

        self.iteration_log_textbox.configure(state="normal") # Aktifkan textbox log agar bisa dimodifikasi (diisi teks)
        self.iteration_log_textbox.delete("1.0", ctk.END) # Hapus semua teks lama di log (dari "1.0" = baris 1 kolom 0, sampai "end")

        # Pastikan tag 'iter_head' sudah terkonfigurasi dengan benar.
        # Seharusnya sudah di __init__, tapi ini untuk jaga-jaga jika ada masalah.
        try:
            # Untuk CTkTextbox, tag_config hanya bisa mengatur foreground, font, dll. tidak background.
            self.iteration_log_textbox.tag_config("iter_head", foreground=self.tag_iter_head_fg_config)
        except Exception as e:
            print(f"Gagal konfigurasi ulang tag di calculate_root: {e}") # Cetak error ke konsol jika gagal

        # Ambil semua nilai input dari kolom-kolom entry
        eq_str = self.equation_entry.get()
        a_s = self.a_entry.get()
        b_s = self.b_entry.get()
        tol_s = self.tol_entry.get()
        max_it_s = self.max_iter_entry.get()

        # Validasi dasar: pastikan semua kolom input terisi
        if not all([eq_str, a_s, b_s, tol_s, max_it_s]):
            messagebox.showerror("Input Error", "Semua kolom input harus diisi.", icon='warning') # Tampilkan popup error
            self.iteration_log_textbox.configure(state="disabled") # Nonaktifkan lagi textbox log
            return # Hentikan proses kalkulasi

        # Panggil fungsi backend bisection_method dengan input yang sudah diambil
        result = bisection_method(eq_str, a_s, b_s, tol_s, max_it_s)

        # Tampilkan log iterasi di textbox dan terapkan styling untuk header iterasi
        if 'iteration_log_text' in result: # Cek apakah ada log teks di hasil
            full_log_content = "".join(result['iteration_log_text']) # Gabungkan semua baris log menjadi satu string besar
            self.iteration_log_textbox.insert("1.0", full_log_content) # Masukkan semua log ke textbox

            # Terapkan tag 'iter_head' ke baris-baris yang merupakan header iterasi
            # Ini dilakukan SETELAH semua teks dimasukkan agar pencarian indeksnya akurat.
            current_char_index = 0 # Untuk melacak posisi karakter global di textbox
            for line_text_from_list in result['iteration_log_text']: # Loop melalui setiap "potongan" log (per append di bisection_method)
                cleaned_line_for_check = line_text_from_list.lstrip('\n').strip() # Bersihkan baris untuk pengecekan

                # Cari baris yang dimulai dengan "====== Iterasi ke-" (sebelumnya "--- Iterasi ke-")
                # PERHATIKAN: Di bisection_method, header log adalah "====== Iterasi ke-". Pastikan konsisten.
                if cleaned_line_for_check.startswith("====== Iterasi ke-"):
                    header_search_string = cleaned_line_for_check # String header yang akan dicari
                    # Tentukan posisi awal pencarian di textbox, berdasarkan current_char_index
                    start_text_index_for_search = self.iteration_log_textbox.index(f"1.0 + {current_char_index}c")
                    # Cari posisi awal string header di textbox
                    found_pos_start = self.iteration_log_textbox.search(header_search_string, start_text_index_for_search, stopindex="end")

                    if found_pos_start: # Jika header ditemukan
                        # Tentukan posisi akhir dari string header
                        found_pos_end = f"{found_pos_start} + {len(header_search_string)}c" # "+ Xc" berarti X karakter setelah posisi awal
                        # Tambahkan tag 'iter_head' ke rentang teks header yang ditemukan
                        self.iteration_log_textbox.tag_add("iter_head", found_pos_start, found_pos_end)

                current_char_index += len(line_text_from_list) # Update posisi karakter global

        self.iteration_log_textbox.configure(state="disabled") # Nonaktifkan kembali textbox log (read-only)

        # Tampilkan pesan error dari backend jika ada
        if 'error' in result:
            messagebox.showerror("Error Kalkulasi", result['error'], icon='cancel') # Popup error
            self.output_notebook.set("Detail Perhitungan Iterasi") # Pindah fokus ke tab log agar user lihat detail errornya
            return # Hentikan

        # Jika tidak ada error, tampilkan hasil di tab "Tabel Ringkasan Iterasi"
        self.result_label.configure(text=f"{result['message']}") # Tampilkan pesan ringkasan (misal "Akar ditemukan...")

        # Siapkan teks untuk info konvergensi
        fin_abs_err = result.get('final_absolute_error') # Ambil error absolut final
        tol_val = result.get('tolerance') # Ambil nilai toleransi yang dihitung
        formatted_fin_abs_err = format_float(fin_abs_err, 10) # Format dengan presisi tinggi
        formatted_tol_val = format_float(tol_val, 10)         # Format dengan presisi tinggi
        conv_txt = (f"Error Absolut Final |cᵢ-cᵢ₋₁| ≈ {formatted_fin_abs_err}. Toleransi Error (ε) = {formatted_tol_val}.\n")

        # Konversi error dan toleransi ke float untuk perbandingan numerik yang aman
        try: fin_abs_err_f = float(fin_abs_err if str(fin_abs_err) != '-' else 'inf') # Jika '-', anggap tak hingga
        except: fin_abs_err_f = float('inf') # Default tak hingga jika konversi gagal
        try: tol_val_f = float(tol_val if str(tol_val) != '-' else 'inf')
        except: tol_val_f = float('inf')

        # Tentukan teks status konvergensi berdasarkan pesan hasil dan perbandingan error
        if "Akar eksak" in result['message'] or "f(c) ≈ 0" in result['message'] or "f(a) ≈ 0" in result['message'] or "f(b) ≈ 0" in result['message'] :
            conv_txt += "Akar ditemukan atau f(x) sangat dekat dengan nol."
        elif fin_abs_err_f < tol_val_f: # Jika error final < toleransi
            conv_txt += "Error Absolut Final < Toleranasi Error (ε) = Konvergen."
        else: # Jika error final >= toleransi
            conv_txt += "Error Absolut Final >= Toleranasi Error (ε)."
            conv_txt += " Mungkin belum konvergen." if "Maks iter" in result['message'] else "" # Tambahan jika karena max iter
        self.convergence_info_label.configure(text=conv_txt) # Tampilkan info konvergensi

        # Isi tabel ringkasan (Treeview) dengan data iterasi dari hasil
        for row_data in result['iterations_data']:
            self.tree.insert("", "end", values=(row_data["n"], row_data["a"], row_data["f(a)"], row_data["b"],
                                                row_data["f(b)"], row_data["c"], row_data["f(c)"],
                                                row_data["Update"], row_data["Abs_Error"], row_data["Rel_Error_Percent"]))
        self.output_notebook.set("Tabel Ringkasan Iterasi") # Pindah fokus ke tab tabel hasil

# --- Main Program Execution ---
if __name__ == "__main__": # Blok ini hanya dieksekusi jika script dijalankan secara langsung (bukan diimpor sebagai modul)
    app = BisectionCalculatorApp() # Buat instance (objek) dari aplikasi GUI kita
    app.mainloop() # Jalankan event loop utama Tkinter (membuat window tampil dan interaktif)
