import customtkinter as ctk
from tkinter import ttk, messagebox, scrolledtext, font as tkfont 
import sympy
from sympy.parsing.sympy_parser import parse_expr, standard_transformations, implicit_multiplication_application, convert_xor
import math
import numpy 
import re 

# Imports untuk Matplotlib Preview
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import io

# --- Backend Logic ---
def to_superscript(text_val):
    text = str(text_val)
    superscript_map = {
        "0": "⁰", "1": "¹", "2": "²", "3": "³", "4": "⁴",
        "5": "⁵", "6": "⁶", "7": "⁷", "8": "⁸", "9": "⁹",
        "-": "⁻", ".": "⋅"
    }
    return "".join(superscript_map.get(char, char) for char in text)

def format_float(value, precision=8):
    if value is None:
        return "-"
    if isinstance(value, str) and value == "-":
        return value
    try:
        f_value = float(value)
        if math.isinf(f_value) or math.isnan(f_value):
            return str(f_value)
        if abs(f_value - round(f_value)) < 1e-9: # Toleransi untuk floating point
            return str(int(round(f_value)))
        # Format ke presisi dulu
        formatted_str = f"{f_value:.{precision}f}"
        # Kemudian hilangkan nol di akhir jika ada bagian desimal
        if '.' in formatted_str:
            integer_part, decimal_part = formatted_str.split('.', 1)
            decimal_part = decimal_part.rstrip('0')
            if not decimal_part: # Jika bagian desimal jadi kosong (misal "1.000" -> "1.")
                return integer_part
            return f"{integer_part}.{decimal_part}"
        else:
            # Seharusnya tidak terjadi jika bukan integer dan diformat dengan presisi
            return formatted_str
    except (ValueError, TypeError):
        return str(value)

def parse_equation_for_lambdify(equation_str):
    try:
        x = sympy.symbols('x')
        equation_str_processed = equation_str.lower().strip()
        if not equation_str_processed:
            raise ValueError("Persamaan tidak boleh kosong.")

        transformations = standard_transformations + (implicit_multiplication_application, convert_xor)
        local_dict_sympy = {
            'x': x, 'sin': sympy.sin, 'cos': sympy.cos, 'tan': sympy.tan,
            'exp': sympy.exp, 'log': sympy.log, 'log10': lambda arg: sympy.log(arg, 10),
            'sqrt': sympy.sqrt, 'abs': sympy.Abs, 'pi': sympy.pi, 'e': sympy.E, 'pow': sympy.Pow
        }
        parsed_expr = parse_expr(equation_str_processed, local_dict=local_dict_sympy, transformations=transformations, evaluate=True)
        if parsed_expr is None: raise ValueError("Gagal mem-parsing ekspresi menjadi None.")

        free_symbols = parsed_expr.free_symbols
        if free_symbols and (free_symbols - {x}):
            unknown_symbols = free_symbols - {x}
            raise ValueError(f"Ditemukan variabel yang tidak dikenal: {', '.join(map(str, unknown_symbols))}. Hanya 'x' yang diizinkan.")

        numerical_modules = [
            {'exp': math.exp, 'log': math.log, 'log10': math.log10,
             'sin': math.sin, 'cos': math.cos, 'tan': math.tan,
             'sqrt': math.sqrt, 'abs': abs, 'pi': math.pi, 'e': math.e, 'pow': pow}, "numpy"
        ]
        try:
            func = sympy.lambdify(x, parsed_expr, modules=numerical_modules)
            try:
                _ = func(1.0) # Tes fungsi
            except TypeError as te: # Jika ekspresi adalah konstanta
                if parsed_expr.is_constant():
                    const_val = float(parsed_expr.evalf())
                    func = lambda val: const_val # Fungsi yang mengembalikan konstanta
                else: # Error lain
                    raise ValueError(f"Ekspresi '{equation_str}' tidak bisa diubah menjadi fungsi dari x. Detail: {te}")
            return func
        except RuntimeError as rterr : # Error dari lambdify
             raise ValueError(f"Error saat membuat fungsi numerik dari '{equation_str}'. Mungkin ada fungsi yang tidak didukung oleh lambdify. Detail: {rterr}")

    except (SyntaxError, TypeError, AttributeError, ValueError) as e:
        error_detail = str(e)
        if isinstance(e, SyntaxError): error_detail = f"Kesalahan sintaks: {e.msg} (dekat '{e.text}')"
        guidance = (f"Error parsing equation (for calculation): {error_detail}\n\n"
                    "Pastikan format benar. Cek tips di GUI.")
        raise ValueError(guidance)
    except Exception as e: # Error tak terduga lainnya
        raise ValueError(f"Error tak terduga saat parsing (for calculation): {str(e)}")

def get_latex_from_equation(equation_str):
    equation_str_processed = str(equation_str).lower().strip()
    if not equation_str_processed:
        return ""
    try:
        x = sympy.symbols('x')
        transformations = standard_transformations + (implicit_multiplication_application, convert_xor)
        local_dict_sympy = {
            'x': x, 'sin': sympy.sin, 'cos': sympy.cos, 'tan': sympy.tan,
            'exp': sympy.exp, 'log': sympy.log, 'log10': sympy.Function('log10'), # log10 sebagai Fungsi Sympy
            'sqrt': sympy.sqrt, 'abs': sympy.Abs, 'pi': sympy.pi, 'e': sympy.E, 'pow': sympy.Pow
        }
        # Evaluate=False agar struktur asli terjaga untuk LaTeX
        parsed_expr = parse_expr(equation_str_processed, local_dict=local_dict_sympy, transformations=transformations, evaluate=False)
        if parsed_expr is None:
             return r"\text{Error: Tidak dapat parsing}" # Pesan error LaTeX
        # Opsi LaTeX untuk tampilan yang lebih baik
        return sympy.latex(parsed_expr, mul_symbol='dot', fold_short_frac=False, long_frac_ratio=2)
    except (SyntaxError, TypeError, AttributeError) as e: # Error parsing umum
        # Logika untuk pratinjau saat mengetik operator di akhir
        if equation_str_processed.endswith(tuple(['^', '**', '*', '/', '+', '-'])):
            base_part, op_char = "", ""
            # Tentukan bagian dasar dan operator
            if equation_str_processed.endswith('^'): base_part, op_char = equation_str_processed[:-1], "^"
            elif equation_str_processed.endswith('**'): base_part, op_char = equation_str_processed[:-2], "**"
            elif equation_str_processed.endswith(tuple(['*', '/', '+', '-'])): base_part, op_char = equation_str_processed[:-1], equation_str_processed[-1]

            if base_part.strip(): # Jika ada bagian dasar
                try:
                    base_expr_preview = parse_expr(base_part.strip(), local_dict=local_dict_sympy, transformations=transformations, evaluate=False)
                    if base_expr_preview:
                        if op_char in ["^", "**"]: return sympy.latex(base_expr_preview, mul_symbol='dot') + r"^{\square}" # Pangkat
                        else: return sympy.latex(base_expr_preview, mul_symbol='dot') + sympy.latex(op_char, mode='plain') + r"\text{ ?}" # Operator lain
                except: pass # Abaikan error di sini, fallback ke pesan umum
            return r"\text{Lanjutkan mengetik...}" # Jika hanya operator atau base_part kosong
        return r"\text{Input tidak valid}" # Error parsing umum
    except Exception: # Error tak terduga lainnya
        return r"\text{Error pratinjau}"


def bisection_method(equation_str, a_str, b_str, tol_str, max_iter_str="100"):
    iteration_log_text = []
    value_precision = 8
    error_precision = 10
    tol = 0.0
    try:
        f = parse_equation_for_lambdify(equation_str)
        a = float(a_str); b = float(b_str)
        if a == b: return {'error': "Interval a dan b tidak boleh sama."}
        if a > b: a, b = b, a; iteration_log_text.append("Info: Nilai a dan b ditukar karena a > b.\n")
        try:
            # Evaluasi toleransi dengan aman
            tol_val_str_eval = tol_str.replace(" ", "")
            # Ganti x^y menjadi x**y untuk eval()
            tol_val_str_eval = re.sub(r'(\d+(?:\.\d+)?(?:[eE][-+]?\d+)?)\s*\^\s*\(?\s*(-?\d+(?:\.\d+)?)\s*\)?', r'\1**\2', tol_val_str_eval)
            tol_val_str_eval = re.sub(r'(\d+(?:\.\d+)?(?:[eE][-+]?\d+)?)\s*\^\s*(-?\d+(?:\.\d+)?)', r'\1**\2', tol_val_str_eval) # Tanpa kurung untuk eksponen

            # Hanya izinkan operasi matematika dasar dan konstanta math
            if any(op in tol_val_str_eval for op in ['**', '/', '*', '+', '-']):
                 tol = float(eval(tol_val_str_eval, {"__builtins__": None}, {"math": math, "e": math.e, "pi": math.pi}))
            else: tol = float(tol_val_str_eval) # Jika hanya angka
            if tol <= 0: return {'error': "Toleransi error (ε) harus lebih besar dari nol."}
        except Exception as e_tol: return {'error': f"Format toleransi tidak valid: '{tol_str}'.\nDetail: {str(e_tol)}"}
        max_iter = int(max_iter_str)
        if max_iter <=0: return {'error': "Maksimum iterasi harus lebih besar dari nol."}
    except ValueError as e: return {'error': str(e)} # Error konversi tipe
    except Exception as e: return {'error': f"Input tidak valid: {str(e)}."} # Error umum lainnya

    # Format toleransi untuk log
    display_tol_for_log = format_float(tol, error_precision)
    original_tol_input = tol_str.strip()
    # Cek jika format toleransi menggunakan ^ atau ** untuk tampilan superscript
    match_caret = re.match(r"^\s*([\d\.]+|[eE]|[pP][iI])\s*\^\s*\(?\s*([-\d\.]+)\s*\)?\s*$", original_tol_input)
    match_star = re.match(r"^\s*([\d\.]+|[eE]|[pP][iI])\s*\*\*\s*\(?\s*([-\d\.]+)\s*\)?\s*$", original_tol_input)
    if match_caret: base, exp = match_caret.groups(); display_tol_for_log = f"{base}{to_superscript(exp)} (dihitung sebagai: {format_float(tol, error_precision)})"
    elif match_star: base, exp = match_star.groups(); display_tol_for_log = f"{base}{to_superscript(exp)} (dihitung sebagai: {format_float(tol, error_precision)})"

    f_a_initial, f_b_initial = f(a), f(b)
    epsilon_zero_check = 1e-12 # Angka kecil untuk perbandingan dengan nol
    # Cek jika a atau b sudah merupakan akar
    if abs(f_a_initial) < epsilon_zero_check:
        iteration_log_text.append(f"Data Awal:\n  f(a) = f({format_float(a, value_precision)}) = {format_float(f_a_initial, value_precision)} ≈ 0. Titik 'a' adalah akar.\n")
        return {'root': format_float(a, value_precision), 'iterations_data': [], 'message': f"Akar ditemukan pada x = {format_float(a, value_precision)} (f(a) ≈ 0).", 'final_absolute_error': 0.0, 'tolerance': tol, 'iteration_log_text': iteration_log_text}
    if abs(f_b_initial) < epsilon_zero_check:
        iteration_log_text.append(f"Data Awal:\n  f(b) = f({format_float(b, value_precision)}) = {format_float(f_b_initial, value_precision)} ≈ 0. Titik 'b' adalah akar.\n")
        return {'root': format_float(b, value_precision), 'iterations_data': [], 'message': f"Akar ditemukan pada x = {format_float(b, value_precision)} (f(b) ≈ 0).", 'final_absolute_error': 0.0, 'tolerance': tol, 'iteration_log_text': iteration_log_text}
    # Cek kondisi f(a) * f(b) < 0
    if f_a_initial * f_b_initial > 0: return {'error': f"f(a) & f(b) tidak beda tanda. f({format_float(a,value_precision)})={format_float(f_a_initial,value_precision)}, f({format_float(b,value_precision)})={format_float(f_b_initial,value_precision)}."}

    iterations_data, c_prev_iter = [], None # c_prev_iter untuk error absolut
    # Log awal
    iteration_log_text.append(f"Data Awal:\n  Persamaan f(x) = {equation_str}\n  Interval awal: [{format_float(a, value_precision)}, {format_float(b, value_precision)}]\n  Toleransi (ε): {display_tol_for_log}\n  f(a) = f({format_float(a, value_precision)}) = {format_float(f_a_initial, value_precision)}\n  f(b) = f({format_float(b, value_precision)}) = {format_float(f_b_initial, value_precision)}\n  Kondisi awal terpenuhi (f(a) * f(b) < 0).\n")

    c = a # Inisialisasi c untuk kasus max_iter = 0 atau sangat kecil
    for n in range(1, max_iter + 1):
        # Baris ini akan diberi gaya bold-italic di GUI
        log_parts = [f"\n\n\n====== Iterasi ke-{n} ======"]
        log_parts.append(f"  Interval saat ini [{format_float(a, value_precision)},{format_float(b, value_precision)}]: a = {format_float(a, value_precision)}, b = {format_float(b, value_precision)}")
        f_a_curr, f_b_curr = f(a), f(b)
        log_parts.extend([f"  f(a) = {format_float(f_a_curr, value_precision)}", f"  f(b) = {format_float(f_b_curr, value_precision)}"])

        # Kondisi berhenti jika interval sangat kecil
        if abs(b-a) < epsilon_zero_check:
            c = (a+b)/2; abs_err = abs(c - c_prev_iter) if c_prev_iter is not None else 0.0
            log_parts.append(f"  Interval [a,b] sudah sangat kecil ({format_float(abs(b-a), error_precision)}). Aproksimasi c = {format_float(c, value_precision)}. Hentikan.")
            tbl_info = {"n":n,"a":format_float(a,value_precision),"f(a)":format_float(f_a_curr,value_precision),"b":format_float(b,value_precision),"f(b)":format_float(f_b_curr,value_precision),"c":format_float(c,value_precision),"f(c)":format_float(f(c),value_precision),"Abs_Error":format_float(abs_err,error_precision),"Rel_Error_Percent":"-","Update":"Interval sgt kecil"}
            iterations_data.append(tbl_info); iteration_log_text.append("\n".join(log_parts))
            return {'root':format_float(c,value_precision),'iterations_data':iterations_data,'message':f"Interval sgt kecil. Aproksimasi x={format_float(c,value_precision)} ({n} iter).",'final_absolute_error':abs_err,'tolerance':tol,'iteration_log_text':iteration_log_text}

        c_calc = (a + b) / 2 # Hitung c
        # Simulasi tampilan pecahan untuk c di log
        val_a_str,val_b_str = format_float(a,value_precision),format_float(b,value_precision)
        sum_ab = a+b; val_sum_ab_str = format_float(sum_ab,value_precision); val_c_str = format_float(c_calc,value_precision)
        num_s1,den_s = f"{val_a_str} + {val_b_str}","2"
        max_len_s1,max_len_s2 = max(len(num_s1),len(den_s)),max(len(val_sum_ab_str),len(den_s))
        c_lbl = "c" # Bisa juga c_n
        log_parts.extend([f"  Perhitungan {c_lbl}:",f"    {c_lbl} =  {num_s1.center(max_len_s1)}",f"          {'-'*max_len_s1}",f"          {den_s.center(max_len_s1)}",f"    {c_lbl} =  {val_sum_ab_str.center(max_len_s2)}  =  {val_c_str}",f"          {'-'*max_len_s2}",f"          {den_s.center(max_len_s2)}",""])
        c = c_calc

        # Kondisi berhenti jika c sama dengan a atau b (batas presisi float)
        if c == a or c == b:
            abs_err = abs(c - c_prev_iter) if c_prev_iter is not None else 0.0
            log_parts.append(f"  Titik tengah c ({format_float(c,value_precision)}) sama dengan a atau b. Batas presisi tercapai.")
            tbl_info = {"n":n,"a":format_float(a,value_precision),"f(a)":format_float(f_a_curr,value_precision),"b":format_float(b,value_precision),"f(b)":format_float(f_b_curr,value_precision),"c":format_float(c,value_precision),"f(c)":format_float(f(c),value_precision),"Abs_Error":format_float(abs_err,error_precision),"Rel_Error_Percent":"-","Update":"Presisi tercapai"}
            iterations_data.append(tbl_info); iteration_log_text.append("\n".join(log_parts))
            return {'root':format_float(c,value_precision),'iterations_data':iterations_data,'message':f"Batas presisi. Aproksimasi x={format_float(c,value_precision)} ({n} iter).",'final_absolute_error':abs_err,'tolerance':tol,'iteration_log_text':iteration_log_text}

        f_c = f(c); log_parts.append(f"  f({c_lbl}) = f({format_float(c, value_precision)}) = {format_float(f_c, value_precision)}")
        abs_err, rel_err_pct = None, None # Inisialisasi error
        # Hitung error jika bukan iterasi pertama
        if c_prev_iter is not None:
            abs_err = abs(c - c_prev_iter)
            log_parts.append(f"  Error Absolut (e) = |{format_float(c,value_precision)} - {format_float(c_prev_iter,value_precision)}| = {format_float(abs_err, error_precision)}")
            if abs(c) > epsilon_zero_check: # Hindari pembagian dengan nol
                rel_err_pct = abs(abs_err/c)*100; log_parts.append(f"  Error Relatif (%) = (|{format_float(abs_err,error_precision)}| / |{format_float(c,value_precision)}|) * 100% = {format_float(rel_err_pct,2)}%") # Relatif error cukup 2 desimal
            else: rel_err_pct = float('inf'); log_parts.append("  Error Relatif (%) = N/A (c ≈ 0)")
        else: log_parts.append("  Error belum dihitung (iterasi pertama).")

        # Data untuk tabel
        tbl_info = {"n":n,"a":format_float(a,value_precision),"f(a)":format_float(f_a_curr,value_precision),"b":format_float(b,value_precision),"f(b)":format_float(f_b_curr,value_precision),"c":format_float(c,value_precision),"f(c)":format_float(f_c,value_precision),"Abs_Error":format_float(abs_err,error_precision) if abs_err is not None else "-","Rel_Error_Percent":f"{format_float(rel_err_pct,2)}%" if rel_err_pct is not None and rel_err_pct!=float('inf') else ("-" if abs_err is None else "N/A")}

        upd_txt = "" # Teks update untuk tabel
        # Kondisi berhenti jika f(c) mendekati nol
        if abs(f_c) < epsilon_zero_check:
            upd_txt = "Akar ditemukan (f(c) ≈ 0)!"
            log_parts.append(f"  Status: {upd_txt} (f(c) = {format_float(f_c, error_precision)})") # f(c) dengan presisi lebih tinggi
            tbl_info["Update"] = upd_txt; iterations_data.append(tbl_info); iteration_log_text.append("\n".join(log_parts))
            return {'root':format_float(c,value_precision),'iterations_data':iterations_data,'message':f"Akar x={format_float(c,value_precision)} ({n} iter, f(c)≈0).",'final_absolute_error':abs_err if abs_err is not None else 0.0,'tolerance':tol,'iteration_log_text':iteration_log_text}

        # Update interval a atau b
        prod_fa_fc, prod_fc_fb = f_a_curr * f_c, f_c * f_b_curr
        if prod_fa_fc < 0: b_new,a_new,upd_txt = c,a,"b = c"
        elif prod_fc_fb < 0: a_new,b_new,upd_txt = c,b,"a = c"
        # Kasus f(a) atau f(b) sangat dekat dengan nol (pengaman)
        elif abs(f_a_curr)<epsilon_zero_check and prod_fc_fb >=0: b_new,a_new,upd_txt = c,a,"b = c (f(a)≈0)"
        elif abs(f_b_curr)<epsilon_zero_check and prod_fa_fc >=0: a_new,b_new,upd_txt = c,b,"a = c (f(b)≈0)"
        else: # Seharusnya tidak terjadi jika f(a)*f(b) < 0 benar
            upd_txt = "Err: Interval?"; log_parts.append(f"  Peringatan: Problem interval. f(a)={format_float(f_a_curr,value_precision)}, f(b)={format_float(f_b_curr,value_precision)}, f(c)={format_float(f_c,value_precision)}")
            tbl_info["Update"] = upd_txt; iterations_data.append(tbl_info); iteration_log_text.append("\n".join(log_parts))
            return {'error':f"Problem interval iter {n}. f(a)f(c)={prod_fa_fc:.2e}, f(c)f(b)={prod_fc_fb:.2e}",'iteration_log_text':iteration_log_text}

        log_parts.append(f"  Update: {upd_txt}. Interval baru: [{format_float(a_new,value_precision)}, {format_float(b_new,value_precision)}]")
        a,b = a_new,b_new # Perbarui a dan b
        tbl_info["Update"] = upd_txt; iterations_data.append(tbl_info); iteration_log_text.append("\n".join(log_parts))
        c_prev_iter_for_next = c # Simpan c saat ini untuk error iterasi berikutnya
        # Kondisi berhenti jika error absolut < toleransi
        if abs_err is not None and abs_err < tol:
            iteration_log_text.append(f"\n\n\nKonvergensi: Error Absolut ({format_float(abs_err,error_precision)}) < Toleransi Error ({format_float(tol,error_precision)})")
            return {'root':format_float(c,value_precision),'iterations_data':iterations_data,'message':f"Konvergen x={format_float(c,value_precision)} (Iterasi Ke-{n}).",'final_absolute_error':abs_err,'tolerance':tol,'iteration_log_text':iteration_log_text}
        c_prev_iter = c_prev_iter_for_next # Update c_prev_iter

    # Jika loop selesai tanpa kondisi berhenti lain (max_iter tercapai)
    final_err = abs_err if abs_err is not None else 0.0 # Error terakhir yang dihitung
    iteration_log_text.append(f"\nPeringatan:\n  Maksimum iterasi ({max_iter}) tercapai.")
    return {'root':format_float(c,value_precision),'iterations_data':iterations_data,'message':f"Maks iter ({max_iter}). Aproksimasi x={format_float(c,value_precision)}.",'final_absolute_error':final_err,'tolerance':tol,'iteration_log_text':iteration_log_text}

# --- Frontend GUI ---
class BisectionCalculatorApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Bisection Method Calculator - New Palette"); self.geometry("1350x900") # Sedikit diperbesar

        # --- Color Palette ---
        self.clr_dark_purple = "#210440"
        self.clr_light_peach_base = "#FDB095"
        self.clr_dusty_rose = "#E5958E"
        self.clr_golden_yellow = "#FFBA00"
        self.clr_white = "#FFFFFF"

        # --- Derived UI Colors ---
        self.app_bg_color = "#FEFBF9" # Peach sangat terang
        self.text_color = self.clr_dark_purple
        self.entry_fg_color = self.clr_white
        self.entry_border_color = self.clr_light_peach_base
        self.entry_text_color = self.clr_dark_purple
        self.button_fg_color = self.clr_dark_purple
        self.button_text_color = self.clr_white
        self.button_hover_color = "#3A1F78" # Ungu lebih terang/modifikasi
        self.accent_color_result = self.clr_dusty_rose # Untuk pesan hasil
        self.log_fg_color = self.clr_white
        self.log_text_color = self.clr_dark_purple
        self.preview_fg_color = "#FDECDC" # Peach lebih muda (tint dari FDB095)

        # --- Treeview Specific Colors ---
        self.tree_heading_bg = self.clr_dark_purple
        self.tree_heading_fg = self.clr_white
        self.tree_row_bg = self.clr_white
        self.tree_row_fg = self.clr_dark_purple
        self.tree_selected_bg = self.clr_golden_yellow
        self.tree_selected_fg = self.clr_dark_purple # Teks pada item terpilih

        # --- Font Configuration ---
        self.font_general_size = 11
        self.font_log_family = "Consolas" # Font utama untuk log
        self.font_log_size = 13
        self.font_log_fallback_family = "Courier New" # Fallback

        try:
            # Cek ketersediaan font (menggunakan tkfont.Font)
            tkfont.Font(family=self.font_log_family, size=self.font_log_size).actual()
            self.actual_log_font_family = self.font_log_family
        except tkfont.tkinter.TclError: # Exception spesifik jika font tidak ada
            self.actual_log_font_family = self.font_log_fallback_family
        except Exception: # Fallback umum
             self.actual_log_font_family = self.font_log_fallback_family

        # Tuple font untuk kemudahan penggunaan
        self.font_log_tuple = (self.actual_log_font_family, self.font_log_size)
        self.font_table_row_tuple = ("Segoe UI", 10)
        self.font_table_heading_tuple = ("Segoe UI", 11, "bold")
        self.font_label_tuple = ("Segoe UI", self.font_general_size)
        self.font_button_tuple = ("Segoe UI", self.font_general_size, "bold")
        self.font_entry_tuple = ("Segoe UI", self.font_general_size)
        self.font_result_label_tuple = ("Segoe UI", 13, "bold") # Font untuk label hasil utama
        self.font_convergence_info_tuple = ("Segoe UI", 10) # Font untuk info konvergensi
        self.font_instruction_tuple = ("Segoe UI", 9) # Font untuk instruksi

        # Konfigurasi warna foreground untuk tag header iterasi
        self.tag_iter_head_fg_config = self.clr_dark_purple # DIGANTI dari kuning ke dusty rose


        ctk.set_appearance_mode("Light") # Mode terang
        self.configure(fg_color=self.app_bg_color) # Latar belakang utama aplikasi

        self.preview_canvas_widget = None # Untuk pratinjau Matplotlib

        # --- Input Frame ---
        self.input_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.input_frame.pack(pady=10, padx=20, fill="x")

        ctk.CTkLabel(self.input_frame, text="Persamaan f(x) = 0:", text_color=self.text_color, font=self.font_label_tuple).grid(row=0, column=0, padx=5, pady=5, sticky="nw")
        self.equation_entry = ctk.CTkEntry(self.input_frame, width=350, placeholder_text="Contoh: x^3 + 4x^2 - 10",
                                           fg_color=self.entry_fg_color, text_color=self.entry_text_color,
                                           border_color=self.entry_border_color, font=self.font_entry_tuple)
        self.equation_entry.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        self.equation_entry.insert(0, "x^3 + 4*x^2 - 10") # Contoh persamaan

        self.refresh_preview_button = ctk.CTkButton(self.input_frame, text="🔄 Pratinjau", width=120,
                                                    command=self.update_equation_preview,
                                                    fg_color=self.button_fg_color, hover_color=self.button_hover_color,
                                                    text_color=self.button_text_color, font=self.font_button_tuple)
        self.refresh_preview_button.grid(row=0, column=2, padx=(10,0), pady=5, sticky="w")

        ctk.CTkLabel(self.input_frame, text="Pratinjau Persamaan:", text_color=self.text_color, font=self.font_label_tuple).grid(row=1, column=0, padx=5, pady=(5,0), sticky="nw")
        self.preview_frame = ctk.CTkFrame(self.input_frame, height=60, fg_color=self.preview_fg_color, corner_radius=5)
        self.preview_frame.grid(row=1, column=1, columnspan=2, padx=5, pady=5, sticky="ew")
        self.preview_frame.grid_propagate(False) # Agar ukuran frame tetap
        self.initial_preview_text_label = ctk.CTkLabel(self.preview_frame, text="Klik '🔄 Pratinjau' untuk melihat",
                                                       text_color=self.text_color, anchor="center", font=self.font_label_tuple)
        self.initial_preview_text_label.pack(expand=True, fill="both", padx=5, pady=5)

        input_row_start = 2 # Baris mulai untuk input a,b, dst.
        ctk.CTkLabel(self.input_frame, text="Interval [a, b]:", text_color=self.text_color, font=self.font_label_tuple).grid(row=input_row_start, column=0, padx=5, pady=5, sticky="w")
        self.a_entry = ctk.CTkEntry(self.input_frame, width=120, fg_color=self.entry_fg_color, text_color=self.entry_text_color, border_color=self.entry_border_color, font=self.font_entry_tuple)
        self.a_entry.grid(row=input_row_start, column=1, padx=5, pady=5, sticky="w"); self.a_entry.insert(0, "1")
        self.b_entry = ctk.CTkEntry(self.input_frame, width=120, fg_color=self.entry_fg_color, text_color=self.entry_text_color, border_color=self.entry_border_color, font=self.font_entry_tuple)
        self.b_entry.grid(row=input_row_start, column=1, padx=(130,5), pady=5, sticky="w"); self.b_entry.insert(0, "1.5")

        ctk.CTkLabel(self.input_frame, text="Toleransi Error (ε):", text_color=self.text_color, font=self.font_label_tuple).grid(row=input_row_start+1, column=0, padx=5, pady=5, sticky="w")
        self.tol_entry = ctk.CTkEntry(self.input_frame, width=180, fg_color=self.entry_fg_color, text_color=self.entry_text_color, border_color=self.entry_border_color, font=self.font_entry_tuple)
        self.tol_entry.grid(row=input_row_start+1, column=1, padx=5, pady=5, sticky="w"); self.tol_entry.insert(0, "0.00001")

        ctk.CTkLabel(self.input_frame, text="Maks Iterasi:", text_color=self.text_color, font=self.font_label_tuple).grid(row=input_row_start+2, column=0, padx=5, pady=5, sticky="w")
        self.max_iter_entry = ctk.CTkEntry(self.input_frame, width=180, fg_color=self.entry_fg_color, text_color=self.entry_text_color, border_color=self.entry_border_color, font=self.font_entry_tuple)
        self.max_iter_entry.grid(row=input_row_start+2, column=1, padx=5, pady=5, sticky="w"); self.max_iter_entry.insert(0, "100")

        # Teks instruksi
        instruction_text = ("Format Persamaan:\n- 'x' sebagai variabel.\n- Perkalian implisit: '4x', 'x(x+1)'.\n- Pangkat: 'x^3' atau 'x**3'.\n- Fungsi: sin,cos,tan,exp,log(ln),log10,sqrt,abs,pow.\n- Konstanta: pi, e.")
        ctk.CTkLabel(self.input_frame, text=instruction_text, text_color=self.text_color, justify="left", wraplength=300, font=self.font_instruction_tuple).grid(row=0, column=3, rowspan=input_row_start+3, padx=(20,5), pady=5, sticky="nw")

        # Tombol Hitung
        self.calculate_button = ctk.CTkButton(self.input_frame, text="Hitung Akar", command=self.calculate_root,
                                              fg_color=self.button_fg_color, hover_color=self.button_hover_color,
                                              text_color=self.button_text_color, font=self.font_button_tuple, height=35)
        self.calculate_button.grid(row=input_row_start+3, column=0, columnspan=3, pady=(15,10))
        self.input_frame.columnconfigure(1, weight=1) # Agar input field bisa expand

        # --- Output Notebook (Tabs) ---
        # Konfigurasi warna untuk CTkTabview
        self.output_notebook = ctk.CTkTabview(self, height=350,
                                             segmented_button_fg_color=self.clr_dark_purple, # Warna tombol tab
                                             segmented_button_selected_color=self.clr_golden_yellow, # Warna tab terpilih
                                             segmented_button_selected_hover_color=self.clr_golden_yellow, # Hover tab terpilih
                                             segmented_button_unselected_color=self.app_bg_color, # Bg tab tidak terpilih
                                             segmented_button_unselected_hover_color=self.preview_fg_color, # Hover tab tidak terpilih
                                             text_color=self.text_color, # Warna teks tab
                                             text_color_disabled=self.clr_light_peach_base # Warna teks tab disabled
                                             )
        self.output_notebook.pack(pady=10, padx=20, fill="both", expand=True)
        self.output_notebook.add("Detail Perhitungan Iterasi")
        self.output_notebook.add("Tabel Ringkasan Iterasi")
        self.output_notebook.set("Detail Perhitungan Iterasi") # Tab default

        # --- Tab Log Iterasi Detail ---
        log_frame = self.output_notebook.tab("Detail Perhitungan Iterasi")
        self.iteration_log_textbox = ctk.CTkTextbox(log_frame, wrap="none", font=self.font_log_tuple,
                                                    fg_color=self.log_fg_color, text_color=self.log_text_color,
                                                    border_width=1, border_color=self.entry_border_color)
        self.iteration_log_textbox.pack(fill="both", expand=True, padx=2, pady=2)
        # Konfigurasi tag setelah widget dibuat. Hanya foreground yang diizinkan.
        self.iteration_log_textbox.tag_config("iter_head", foreground=self.tag_iter_head_fg_config)
        self.iteration_log_textbox.configure(state="disabled")


        # --- Tab Tabel Ringkasan Iterasi ---
        table_frame = self.output_notebook.tab("Tabel Ringkasan Iterasi")
        self.result_label = ctk.CTkLabel(table_frame, text="", text_color=self.accent_color_result, font=self.font_result_label_tuple, wraplength=1000, justify="left")
        self.result_label.pack(pady=(10,5), anchor="w", padx=5)
        self.convergence_info_label = ctk.CTkLabel(table_frame, text="", text_color=self.text_color, font=self.font_convergence_info_tuple, wraplength=1000, justify="left")
        self.convergence_info_label.pack(pady=5, anchor="w", padx=5)

        columns = ("Iterasi", "a", "f(a)", "b", "f(b)", "c", "f(c)", "Update", "Error Absolut", "Error Relatif(%)")
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings", style="Custom.Treeview")

        # Konfigurasi style untuk Treeview (ttk)
        style_tree = ttk.Style()
        style_tree.theme_use("clam") # Tema 'clam' lebih fleksibel untuk kustomisasi
        style_tree.configure("Custom.Treeview.Heading", # Style untuk header kolom
                             font=self.font_table_heading_tuple,
                             background=self.tree_heading_bg,
                             foreground=self.tree_heading_fg,
                             padding=(5,5), anchor="center")
        style_tree.configure("Custom.Treeview", # Style untuk baris data
                             background=self.tree_row_bg,
                             foreground=self.tree_row_fg,
                             fieldbackground=self.tree_row_bg, # Background sel data
                             rowheight=28, # Tinggi baris disesuaikan
                             font=self.font_table_row_tuple)
        style_tree.map('Custom.Treeview', # Style untuk item terpilih
                       background=[('selected', self.tree_selected_bg)],
                       foreground=[('selected', self.tree_selected_fg)])

        # Lebar kolom disesuaikan
        col_widths = [40, 95, 95, 95, 95, 115, 115, 95, 115, 100]
        for col, wd in zip(columns, col_widths):
            self.tree.heading(col, text=col, anchor="center") # Teks header di tengah
            self.tree.column(col, width=wd, anchor="center", minwidth=40) # Data di tengah
        self.tree.pack(fill="both", expand=True, pady=(5,0), padx=5)

        # Scrollbar untuk Treeview dengan warna kustom
        tree_scr_y = ctk.CTkScrollbar(self.tree, command=self.tree.yview, button_color=self.button_fg_color, button_hover_color=self.button_hover_color)
        tree_scr_y.pack(side="right", fill="y")
        tree_scr_x = ctk.CTkScrollbar(self.tree, command=self.tree.xview, orientation="horizontal", button_color=self.button_fg_color, button_hover_color=self.button_hover_color)
        tree_scr_x.pack(side="bottom", fill="x")
        self.tree.configure(yscrollcommand=tree_scr_y.set, xscrollcommand=tree_scr_x.set)

    def update_equation_preview(self):
        # Hapus pratinjau lama jika ada
        if self.preview_canvas_widget:
            self.preview_canvas_widget.destroy(); self.preview_canvas_widget = None
        if hasattr(self, 'initial_preview_text_label') and self.initial_preview_text_label.winfo_exists():
            self.initial_preview_text_label.pack_forget()

        eq_str = self.equation_entry.get()
        if not eq_str.strip(): # Jika input kosong, tampilkan teks default
            self.initial_preview_text_label = ctk.CTkLabel(self.preview_frame, text="Klik '🔄 Pratinjau' untuk melihat",
                                                           text_color=self.text_color, anchor="center", font=self.font_label_tuple)
            self.initial_preview_text_label.pack(expand=True, fill="both", padx=5, pady=5)
            return

        try:
            latex_str = get_latex_from_equation(eq_str)
            fig = Figure(figsize=(6, 0.6), dpi=100, facecolor=self.preview_fg_color) # Latar belakang pratinjau
            ax = fig.add_subplot(111)
            ax.clear()
            text_color_preview = self.text_color # Warna teks default untuk pratinjau
            font_size_preview = 12

            # Tentukan teks dan warna berdasarkan hasil parsing LaTeX
            if not latex_str: text_to_render, text_color_preview, font_size_preview = r"$\text{Input tidak valid untuk pratinjau.}$", self.clr_golden_yellow, 9
            elif latex_str.strip().startswith(r"\text{"): # Jika hasil parsing adalah teks error dari get_latex_from_equation
                text_to_render = "$" + latex_str + "$"
                text_color_preview = self.clr_dusty_rose if "Error" in latex_str or "valid" in latex_str else self.clr_golden_yellow
                font_size_preview = 9
            else: text_to_render = f"${latex_str}$" # LaTeX valid

            ax.text(0.5, 0.5, text_to_render, fontsize=font_size_preview, va='center', ha='center', color=text_color_preview, wrap=True)
            ax.axis('off'); fig.tight_layout(pad=0.05) # Layout rapat
            canvas = FigureCanvasTkAgg(fig, master=self.preview_frame)
            self.preview_canvas_widget = canvas.get_tk_widget()
            self.preview_canvas_widget.pack(side=ctk.TOP, fill=ctk.BOTH, expand=True, padx=2, pady=2)
            canvas.draw()
        except Exception as e: # Error umum saat membuat pratinjau
            if self.preview_canvas_widget: self.preview_canvas_widget.destroy(); self.preview_canvas_widget = None
            self.initial_preview_text_label = ctk.CTkLabel(self.preview_frame, text=f"Error Pratinjau Umum: {str(e)[:50]}", # Tampilkan sebagian error
                                                           text_color=self.clr_dusty_rose, font=("Segoe UI",9), anchor="center")
            self.initial_preview_text_label.pack(expand=True, fill="both", padx=5, pady=5)

    def calculate_root(self):
        # Bersihkan output lama
        for i in self.tree.get_children(): self.tree.delete(i)
        self.result_label.configure(text="")
        self.convergence_info_label.configure(text="")

        self.iteration_log_textbox.configure(state="normal") # Aktifkan untuk modifikasi
        self.iteration_log_textbox.delete("1.0", ctk.END) # Hapus log lama

        # Pastikan tag dikonfigurasi (seharusnya sudah di __init__, tapi untuk keamanan)
        try:
            # Hanya foreground yang diizinkan
            self.iteration_log_textbox.tag_config("iter_head", foreground=self.tag_iter_head_fg_config)
        except Exception as e:
            print(f"Gagal konfigurasi ulang tag di calculate_root: {e}")

        # Ambil input
        eq_str = self.equation_entry.get(); a_s = self.a_entry.get(); b_s = self.b_entry.get()
        tol_s = self.tol_entry.get(); max_it_s = self.max_iter_entry.get()
        if not all([eq_str, a_s, b_s, tol_s, max_it_s]): # Validasi input tidak kosong
            messagebox.showerror("Input Error", "Semua kolom input harus diisi.", icon='warning')
            self.iteration_log_textbox.configure(state="disabled"); return

        result = bisection_method(eq_str, a_s, b_s, tol_s, max_it_s) # Panggil metode biseksi

        # Tampilkan log dan terapkan styling
        if 'iteration_log_text' in result:
            full_log_content = "".join(result['iteration_log_text']) # Gabungkan semua baris log
            self.iteration_log_textbox.insert("1.0", full_log_content) # Masukkan semua log sekaligus

            # Terapkan tag ke header iterasi setelah semua teks dimasukkan
            current_char_index = 0
            for line_text_from_list in result['iteration_log_text']:
                cleaned_line_for_check = line_text_from_list.lstrip('\n').strip()

                if cleaned_line_for_check.startswith("--- Iterasi ke-"):
                    header_search_string = cleaned_line_for_check
                    start_text_index_for_search = self.iteration_log_textbox.index(f"1.0 + {current_char_index}c")
                    found_pos_start = self.iteration_log_textbox.search(header_search_string, start_text_index_for_search, stopindex="end")

                    if found_pos_start:
                        found_pos_end = f"{found_pos_start} + {len(header_search_string)}c"
                        self.iteration_log_textbox.tag_add("iter_head", found_pos_start, found_pos_end)

                current_char_index += len(line_text_from_list)

        self.iteration_log_textbox.configure(state="disabled") # Nonaktifkan kembali textbox log

        # Tampilkan error jika ada
        if 'error' in result:
            messagebox.showerror("Error Kalkulasi", result['error'], icon='cancel')
            self.output_notebook.set("Detail Perhitungan Iterasi"); return # Fokus ke tab log

        # Tampilkan hasil dan info konvergensi
        self.result_label.configure(text=f"{result['message']}")
        fin_abs_err, tol_val = result.get('final_absolute_error'), result.get('tolerance')
        formatted_fin_abs_err = format_float(fin_abs_err, 10) # Presisi tinggi untuk error
        formatted_tol_val = format_float(tol_val, 10)     # Presisi tinggi untuk toleransi
        conv_txt = (f"Error Absolut Final |cᵢ-cᵢ₋₁| ≈ {formatted_fin_abs_err}. Toleransi Error (ε) = {formatted_tol_val}.\n")

        # Konversi ke float untuk perbandingan numerik
        try: fin_abs_err_f = float(fin_abs_err if str(fin_abs_err) != '-' else 'inf')
        except: fin_abs_err_f = float('inf')
        try: tol_val_f = float(tol_val if str(tol_val) != '-' else 'inf')
        except: tol_val_f = float('inf')

        # Teks status konvergensi
        if "Akar eksak" in result['message'] or "f(c) ≈ 0" in result['message'] or "f(a) ≈ 0" in result['message'] or "f(b) ≈ 0" in result['message'] : conv_txt += "Akar ditemukan atau f(x) sangat dekat dengan nol."
        elif fin_abs_err_f < tol_val_f: conv_txt += "Error Absolut Final < Toleranasi Error (ε) = Konvergen."
        else: conv_txt += "Error Absolut Final >= Toleranasi Error (ε)."; conv_txt += " Mungkin belum konvergen." if "Maks iter" in result['message'] else ""
        self.convergence_info_label.configure(text=conv_txt)

        # Isi tabel ringkasan
        for row_data in result['iterations_data']:
            self.tree.insert("", "end", values=(row_data["n"], row_data["a"], row_data["f(a)"], row_data["b"],
                                                row_data["f(b)"], row_data["c"], row_data["f(c)"],
                                                row_data["Update"], row_data["Abs_Error"], row_data["Rel_Error_Percent"]))
        self.output_notebook.set("Tabel Ringkasan Iterasi") # Fokus ke tab tabel

if __name__ == "__main__":
    app = BisectionCalculatorApp()
    app.mainloop()