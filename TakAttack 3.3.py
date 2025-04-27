import tkinter as tk
from tkinter import filedialog, messagebox
import pyautogui
import time
import threading
import json
import os
from collections import Counter

ROULETTE = [0, 32, 15, 19, 4, 21, 2, 25, 17, 34, 6, 27,
            13, 36, 11, 30, 8, 23, 10, 5, 24, 16, 33, 1,
            20, 14, 31, 9, 22, 18, 29, 7, 28, 12, 35, 3, 26]

def get_minisector(n):
    """Restituisce il numero centrale con i suoi vicini di ruota"""
    try:
        i = ROULETTE.index(n)
        return [ROULETTE[i-1], n, ROULETTE[(i+1)%len(ROULETTE)]]
    except ValueError:
        return []

def analisi_blocchi_dinamici(spins, modulo=37, window_size=25):
    ultimi = spins[-window_size:]
    blocchi = []
    
    for i in range(len(ultimi)):
        blocco = [ultimi[i]]
        for j in range(i+1, len(ultimi)):
            diff = abs(ultimi[j] - blocco[-1])
            
            if modulo == 36:
                if (blocco[0] % 2 == ultimi[j] % 2) and (diff % 36 in {10, 26}):
                    blocco.append(ultimi[j])
            elif modulo == 37 and 7 <= diff <= 13:
                blocco.append(ultimi[j])
        
        if len(blocco) >= 3:
            if modulo == 36:
                step = 10 if blocco[0] % 2 == 0 else 10
                blocco = sorted({blocco[0] + k*step for k in range(4)} & set(range(37)))
            blocchi.append(blocco)
    
    blocchi.sort(key=len, reverse=True)
    return list(set().union(*blocchi[:2]))[:3]

def strategia_originale(spins):
    """Prima versione della strategia avanzata"""
    params = {
        'window_size': 180,
        'top_numbers': 7,
        'hot_numbers': 2,
        'max_final': 12
    }

    if len(spins) < params['window_size']:
        return {'prediction': [], 'analisi': {}, 'strong_numbers': []}

    freq = Counter(spins[-params['window_size']:])
    top_numeri = [n for n,_ in freq.most_common(params['top_numbers'])]
    
    # Minisettori
    hot_numeri = [n for n,_ in freq.most_common(params['hot_numbers'])]
    minisector_nums = []
    for h in hot_numeri:
        minisector_nums.extend(get_minisector(h))
    
    # Moduli
    mod36_top = [m for m,_ in Counter([x%36 for x in spins[-params['window_size']:]]).most_common(3)]
    mod37_top = [m for m,_ in Counter([x%37 for x in spins[-params['window_size']:]]).most_common(3)]
    mod_nums = {n for n in range(37) if (n%36 in mod36_top) or (n%37 in mod37_top)}
    
    # Freddi
    last_50 = spins[-50:] if len(spins) >= 50 else spins
    freddi = [n for n in range(37) if n not in last_50][:3]

    # Combinazione
    combined = Counter()
    for n in top_numeri: combined[n] += 1.2
    for n in mod_nums: combined[n] += 1.0
    for n in minisector_nums: combined[n] += 1.5
    for n in freddi: combined[n] += 0.8

    strong_numbers = [n for n in combined if sum(
        n in a for a in [top_numeri, mod_nums, minisector_nums, freddi]
    ) >= 2]

    prediction = sorted(set(
        [n for n,_ in combined.most_common(params['max_final'])] +
        strong_numbers
    ))[:params['max_final']]

    return {
        'prediction': prediction,
        'analisi': {
            'Frequenze': top_numeri,
            'Moduli': sorted(mod_nums),
            'Minisettori': list(set(minisector_nums)),
            'Freddi': freddi
        },
        'strong_numbers': strong_numbers
    }

def strategia_blocchi(spins):
    """Seconda versione con blocchi dinamici"""
    params = {
        'window_size': 180,
        'top_numbers': 5,
        'hot_numbers': 2,
        'cold_threshold': 50,
        'max_prediction': 8
    }

    if len(spins) < params['window_size']:
        return {'prediction': [], 'analisi': {}, 'strong_numbers': []}

    # 1. Frequenze
    freq = Counter(spins[-params['window_size']:])
    top_numeri = [n for n,_ in freq.most_common(params['top_numbers'])]

    # 2. Minisettori
    hot_numeri = [n for n,_ in freq.most_common(params['hot_numbers'])]
    minisector_nums = []
    for h in hot_numeri:
        minisector_nums.extend(get_minisector(h))

    # 3. Blocchi Dinamici
    blocchi_mod37 = analisi_blocchi_dinamici(spins, modulo=37)
    blocchi_mod36 = analisi_blocchi_dinamici(spins, modulo=36)

    # 4. Freddi
    last_spins = spins[-params['cold_threshold']:] if len(spins) >= params['cold_threshold'] else spins
    freddi = [n for n in range(37) if n not in last_spins][:2]

    # Numeri forti
    strong_numbers = list(set(
        [n for n in top_numeri if n in minisector_nums] +
        [n for n in blocchi_mod37 if n in blocchi_mod36] +
        [n for n in top_numeri if n in freddi]
    ))

    # Combinazione
    prediction = sorted(
        list(set(
            top_numeri[:3] +
            minisector_nums[:3] +
            blocchi_mod37 +
            blocchi_mod36 +
            freddi +
            strong_numbers
        ))
    )[:params['max_prediction']]

    return {
        'prediction': prediction,
        'analisi': {
            'Frequenze': top_numeri,
            'Minisettori': list(set(minisector_nums)),
            'Blocchi_MOD37': blocchi_mod37,
            'Blocchi_MOD36': blocchi_mod36,
            'Freddi': freddi,
            'Convergenze': list(set(blocchi_mod36) & set(blocchi_mod37))
        },
        'strong_numbers': strong_numbers
    }

def strategia_ibrida(spins):
    """Mix delle due strategie"""
    params = {
        'window_size': 180,
        'top_numbers': 6,
        'hot_numbers': 2,
        'cold_threshold': 50,
        'max_prediction': 10
    }

    if len(spins) < params['window_size']:
        return {'prediction': [], 'analisi': {}, 'strong_numbers': []}

    # 1. Frequenze
    freq = Counter(spins[-params['window_size']:])
    top_numeri = [n for n, _ in freq.most_common(params['top_numbers'])]

    # 2. Minisettori
    hot_numeri = [n for n, _ in freq.most_common(params['hot_numbers'])]
    minisector_nums = []
    for h in hot_numeri:
        minisector_nums.extend(get_minisector(h))

    # 3. Blocchi Dinamici
    blocchi_mod37 = analisi_blocchi_dinamici(spins, modulo=37)
    blocchi_mod36 = analisi_blocchi_dinamici(spins, modulo=36)

    # 4. Freddi
    last_spins = spins[-params['cold_threshold']:] if len(spins) >= params['cold_threshold'] else spins
    freddi = [n for n in range(37) if n not in last_spins][:3]

    # 5. Moduli
    mod36_top = [m for m, _ in Counter([x%36 for x in spins[-params['window_size']:]]).most_common(3)]
    mod37_top = [m for m, _ in Counter([x%37 for x in spins[-params['window_size']:]]).most_common(3)]
    mod_nums = {n for n in range(37) if (n%36 in mod36_top) or (n%37 in mod37_top)}

    # Combinazione con pesi
    combined = Counter()
    for n in top_numeri: combined[n] += 1.2
    for n in minisector_nums: combined[n] += 1.5
    for n in blocchi_mod37: combined[n] += 1.3
    for n in blocchi_mod36: combined[n] += 1.3
    for n in mod_nums: combined[n] += 1.0
    for n in freddi: combined[n] += 0.8

    # Numeri forti
    strong_numbers = [
        n for n in combined if sum(
            n in a for a in [top_numeri, minisector_nums, blocchi_mod37, blocchi_mod36, mod_nums, freddi]
        ) >= 2
    ]

    # Predizione
    prediction = sorted(
        list(set(
            [n for n, _ in combined.most_common(params['max_prediction'])] +
            strong_numbers
        ))
    )[:params['max_prediction']]

    return {
        'prediction': prediction,
        'analisi': {
            'Frequenze': top_numeri,
            'Minisettori': list(set(minisector_nums)),
            'Blocchi_MOD37': blocchi_mod37,
            'Blocchi_MOD36': blocchi_mod36,
            'Moduli': sorted(mod_nums),
            'Freddi': freddi,
            'Convergenze': list(set(blocchi_mod36) & set(blocchi_mod37))
        },
        'strong_numbers': strong_numbers
    }

class RouletteApp:
    def __init__(self, root):
        self.root = root
        self.ultimi_spin = []
        self.ultima_previsione = None
        self.buttons = {}
        self.spin_labels = []
        
        # Variabili mappatura
        self.mappatura_attiva = False
        self.numero_corrente_mappatura = 0
        self.mappa_tavolo = {}

        # Configurazione colori
        self.BG_COLOR = "#404040"
        self.colori = {
            0: "#008000", 1: "#FF0000", 2: "#000000", 3: "#FF0000", 4: "#000000", 
            5: "#FF0000", 6: "#000000", 7: "#FF0000", 8: "#000000", 
            9: "#FF0000", 10: "#000000", 11: "#000000", 12: "#FF0000", 
            13: "#000000", 14: "#FF0000", 15: "#000000", 16: "#FF0000", 
            17: "#000000", 18: "#FF0000", 19: "#FF0000", 20: "#000000", 
            21: "#FF0000", 22: "#000000", 23: "#FF0000", 24: "#000000", 
            25: "#FF0000", 26: "#000000", 27: "#FF0000", 28: "#000000", 
            29: "#000000", 30: "#FF0000", 31: "#000000", 32: "#FF0000", 
            33: "#000000", 34: "#FF0000", 35: "#000000", 36: "#FF0000"
        }
        
        self.COLORI_ANALISI = {
            'Previsione': '#00FFFF', 'Frequenze': '#FFA500', 'Minisettori': '#AA00FF',
            'Freddi': '#00FF00', 'Convergenze': '#FF00FF', 'Numeri Forti': '#00AAFF',
            'Moduli': '#FFCC00', 'Blocchi_MOD37': '#CC00FF', 'Blocchi_MOD36': '#00CCFF'
        }
        
        # Strategie disponibili
        self.strategie = {
            'Originale': strategia_originale,
            'Blocchi': strategia_blocchi,
            'Ibrida': strategia_ibrida
        }
        self.strategia_selezionata = tk.StringVar(value='Ibrida')
        
        self.setup_ui()
        self.root.attributes('-topmost', True)

    def setup_ui(self):
        self.root.title("TakAttack 3.3")
        self.root.geometry("600x550")
        self.root.configure(bg=self.BG_COLOR)
        self.root.resizable(False, False)
        
        # Frame principale per organizzare i componenti
        main_frame = tk.Frame(self.root, bg=self.BG_COLOR)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # ===== TASTIERINO NUMERICO =====
        tappeto_frame = tk.Frame(main_frame, bg=self.BG_COLOR)
        tappeto_frame.pack(pady=(0, 10))
        
        # Pulsanti in alto centrati sopra il tastierino
        control_frame = tk.Frame(tappeto_frame, bg=self.BG_COLOR)
        control_frame.pack(pady=(0, 5))
        
        buttons = [
            ("📥 Carica", self.carica_file),
            ("↩️ Annulla", self.annulla_ultimo),
            ("🔄 Reset", self.reset_all),
            ("🔮 Analisi", self.mostra_previsione)
        ]
        
        for text, cmd in buttons:
            btn = tk.Button(control_frame, text=text, command=cmd, 
                          font=('Arial', 9), width=8, bg="#505050", fg="white")
            btn.pack(side=tk.LEFT, padx=2)
        
        # Selezione strategia
        strategy_frame = tk.Frame(control_frame, bg=self.BG_COLOR)
        strategy_frame.pack(side=tk.LEFT, padx=10)
        
        tk.Label(strategy_frame, text="Strategia:", bg=self.BG_COLOR, fg="white").pack(side=tk.LEFT)
        
        for strategy in self.strategie:
            rb = tk.Radiobutton(
                strategy_frame, text=strategy, variable=self.strategia_selezionata,
                value=strategy, bg=self.BG_COLOR, fg="white", selectcolor="#505050"
            )
            rb.pack(side=tk.LEFT, padx=2)
        
        # Visualizzazione ultimi spin
        spin_frame = tk.Frame(tappeto_frame, bg=self.BG_COLOR)
        spin_frame.pack(pady=5)
        
        for i in range(13):
            lbl = tk.Label(spin_frame, text="", width=3, relief="ridge", 
                         bg="#606060", fg="white", font=('Arial', 10))
            lbl.grid(row=0, column=i, padx=1)
            self.spin_labels.append(lbl)
        
        # Tastierino numeri
        tappeto = tk.Frame(tappeto_frame, bg=self.BG_COLOR)
        tappeto.pack()
        
        # Bottone 0
        self.btn_0 = tk.Button(tappeto, text="0", bg="#008000", fg="white", 
                             width=4, font=('Arial', 10), 
                             command=lambda: self.aggiungi_spin(0))
        self.btn_0.grid(row=0, column=0, rowspan=3, padx=2)
        
        # Numeri 1-36
        for i in range(12):
            col = i + 1
            for r, n in zip([2, 1, 0], [3*i + 1, 3*i + 2, 3*i + 3]):
                bg = self.colori[n]
                fg = "black" if bg == "#FF0000" else "white"
                b = tk.Button(tappeto, text=str(n), width=3, bg=bg, fg=fg,
                            font=('Arial', 10), command=lambda num=n: self.aggiungi_spin(num))
                b.grid(row=r, column=col, padx=1, pady=1)
                self.buttons[n] = b
        
        # ===== BARRE ANALISI (centrate sopra il tastierino) =====
        analysis_frame = tk.Frame(tappeto_frame, bg=self.BG_COLOR)
        analysis_frame.pack(fill=tk.X, pady=(10, 5))
        
        self.analisi_vars = {}
        self.result_frames = {}
        
        options = [
            ('Previsione', '#00FFFF'),
            ('Frequenze', '#FFA500'),
            ('Minisettori', '#AA00FF'),
            ('Freddi', '#00FF00'),
            ('Convergenze', '#FF00FF'),
            ('Numeri Forti', '#00AAFF'),
            ('Moduli', '#FFCC00'),
            ('Blocchi_MOD37', '#CC00FF'),
            ('Blocchi_MOD36', '#00CCFF')
        ]
        
        for name, color in options:
            frame = tk.Frame(analysis_frame, bg=color, bd=1, relief='flat')
            frame.pack(fill=tk.X, pady=1)
            self.result_frames[name] = frame
            
            self.analisi_vars[name] = tk.BooleanVar(value=True)
            cb = tk.Checkbutton(frame, text=name, variable=self.analisi_vars[name],
                              command=self.aggiorna_evidenziazione,
                              fg="black", bg=color, font=('Arial', 9))
            cb.pack(side=tk.LEFT, padx=5)
            
            lbl = tk.Label(frame, text="", font=('Arial', 9), 
                         fg="black", bg=color, anchor="w")
            lbl.pack(side=tk.LEFT, fill=tk.X, expand=True)
            self.result_frames[name + "_label"] = lbl
        
        # ===== PULSANTI MAPPA/PUNTA =====
        bottom_frame = tk.Frame(main_frame, bg=self.BG_COLOR)
        bottom_frame.pack(fill=tk.X, pady=(5, 0))
        
        # Riga 1: Mappatura
        mappa_frame = tk.Frame(bottom_frame, bg=self.BG_COLOR)
        mappa_frame.pack(pady=(5, 0))
        
        self.btn_mappatura = tk.Button(
            mappa_frame, text="🗺️ Avvia Mappatura", 
            command=self.inizia_mappatura,
            width=15, bg="#FF7700", fg="black"
        )
        self.btn_mappatura.pack(side=tk.LEFT, padx=2)
        
        self.btn_registra_posizione = tk.Button(
            mappa_frame, text="📍 Registra Posizione", 
            command=self.cattura_posizione_mouse,
            width=18, bg="#808080", fg="white"
        )
        self.btn_registra_posizione.pack(side=tk.LEFT, padx=2)
        
        self.btn_vedi_mappa = tk.Button(
            mappa_frame, text="👁️ Vedi Mappa", 
            command=self.mostra_overlay_mappatura,
            width=12, bg="#666666", fg="white"
        )
        self.btn_vedi_mappa.pack(side=tk.LEFT, padx=2)
        
        # Riga 2: Salva/Carica
        mappa_frame2 = tk.Frame(bottom_frame, bg=self.BG_COLOR)
        mappa_frame2.pack(pady=(5, 0))
        
        self.btn_salva_mappa = tk.Button(
            mappa_frame2, text="💾 Salva Mappatura", 
            command=self.salva_mappatura,
            width=18, bg="#0066CC", fg="white"
        )
        self.btn_salva_mappa.pack(side=tk.LEFT, padx=2)
        
        self.btn_carica_mappa = tk.Button(
            mappa_frame2, text="📂 Carica Mappatura", 
            command=self.carica_mappatura,
            width=18, bg="#0066CC", fg="white"
        )
        self.btn_carica_mappa.pack(side=tk.LEFT, padx=2)
        
        # Riga 3: Puntate
        punta_frame = tk.Frame(bottom_frame, bg=self.BG_COLOR)
        punta_frame.pack(pady=(5, 10))
        
        self.btn_punta_normale = tk.Button(
            punta_frame, text="Punta Normale", 
            command=lambda: self.esegui_puntata("normale"),
            width=12, bg="#505050", fg="white", state=tk.DISABLED
        )
        self.btn_punta_normale.pack(side=tk.LEFT, padx=2)
        
        self.btn_punta_convergenti = tk.Button(
            punta_frame, text="Punta Convergenti", 
            command=lambda: self.esegui_puntata("convergenti"),
            width=14, bg="#505050", fg="white", state=tk.DISABLED
        )
        self.btn_punta_convergenti.pack(side=tk.LEFT, padx=2)
        
        self.btn_punta_solo_convergenti = tk.Button(
            punta_frame, text="Solo Convergenti", 
            command=lambda: self.esegui_puntata("solo_convergenti"),
            width=14, bg="#505050", fg="white", state=tk.DISABLED
        )
        self.btn_punta_solo_convergenti.pack(side=tk.LEFT, padx=2)
        
        # Status bar
        self.status_label = tk.Label(main_frame, text="Pronto", bg=self.BG_COLOR, fg="white", font=('Arial', 10))
        self.status_label.pack(fill=tk.X, pady=5)

    # ===== METODI MAPPA =====
    def inizia_mappatura(self):
        self.mappatura_attiva = True
        self.numero_corrente_mappatura = 0
        self.mappa_tavolo = {}
        self.status_label.config(text="Mappatura attiva - Premi 'Registra Posizione'")
        self.btn_mappatura.config(text=f"▶ Mappando: 0", bg="#FF7700")

    def cattura_posizione_mouse(self):
        if not self.mappatura_attiva:
            return

        numero = self.numero_corrente_mappatura
        self.status_label.config(text=f"Posiziona il mouse sul numero {numero} entro 3 secondi...")
        threading.Thread(target=self._attendi_e_registra, args=(numero,)).start()

    def _attendi_e_registra(self, numero):
        time.sleep(3)
        pos = pyautogui.position()
        self.mappa_tavolo[numero] = (pos.x, pos.y)
        self.numero_corrente_mappatura += 1

        self.status_label.config(text=f"Registrato numero {numero} a ({pos.x}, {pos.y})")
        self.btn_mappatura.config(text=f"▶ Mappando: {self.numero_corrente_mappatura}" if self.numero_corrente_mappatura <= 36 else "🗺️ Mappatura")

        if self.numero_corrente_mappatura > 36:
            self.mappatura_attiva = False
            self.status_label.config(text="Mappatura completata!")
            # Abilita pulsanti puntata
            for btn in [self.btn_punta_normale, self.btn_punta_convergenti, self.btn_punta_solo_convergenti]:
                btn.config(state=tk.NORMAL)

    def mostra_overlay_mappatura(self):
        if not self.mappa_tavolo:
            messagebox.showwarning("Attenzione", "Mappatura non ancora completata!")
            return

        overlay = tk.Toplevel(self.root)
        overlay.title("Mappa Posizioni")
        overlay.geometry("600x400")
        overlay.attributes('-topmost', True)
        
        canvas = tk.Canvas(overlay, bg="black")
        canvas.pack(fill=tk.BOTH, expand=True)
        
        for numero, (x, y) in self.mappa_tavolo.items():
            # Scala le coordinate per adattarle alla finestra
            x_scaled = x * 0.3
            y_scaled = y * 0.3
            canvas.create_oval(x_scaled-5, y_scaled-5, x_scaled+5, y_scaled+5, fill="red")
            canvas.create_text(x_scaled, y_scaled-10, text=str(numero), fill="white")

    def salva_mappatura(self):
        if not self.mappa_tavolo:
            messagebox.showwarning("Attenzione", "Nessuna mappatura da salvare!")
            return

        file_path = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("File JSON", "*.json"), ("Tutti i file", "*.*")],
            title="Salva mappatura come..."
        )
        
        if not file_path:
            return

        try:
            with open(file_path, 'w') as f:
                json.dump(self.mappa_tavolo, f)
            messagebox.showinfo("Successo", f"Mappatura salvata in:\n{file_path}")
        except Exception as e:
            messagebox.showerror("Errore", f"Errore nel salvataggio:\n{str(e)}")

    def carica_mappatura(self):
        file_path = filedialog.askopenfilename(
            filetypes=[("File JSON", "*.json"), ("Tutti i file", "*.*")],
            title="Seleziona file mappatura"
        )
        
        if not file_path:
            return

        try:
            with open(file_path, 'r') as f:
                self.mappa_tavolo = json.load(f)
            
            # Convertiamo le chiavi da stringhe a interi
            self.mappa_tavolo = {int(k): v for k, v in self.mappa_tavolo.items()}
            
            messagebox.showinfo("Successo", f"Mappatura caricata da:\n{file_path}")
            
            # Abilita pulsanti puntata se la mappatura è completa
            if len(self.mappa_tavolo) >= 37:
                for btn in [self.btn_punta_normale, self.btn_punta_convergenti, self.btn_punta_solo_convergenti]:
                    btn.config(state=tk.NORMAL)
                    
        except Exception as e:
            messagebox.showerror("Errore", f"Errore nel caricamento:\n{str(e)}")

    # ===== METODI PUNTATE =====
    def esegui_puntata(self, tipo):
        if not self.ultima_previsione:
            messagebox.showerror("Errore", "Esegui prima un'analisi!")
            return

        if not self.mappa_tavolo:
            messagebox.showerror("Errore", "Mappatura non disponibile!")
            return

        numeri_da_puntare = self.calcola_numeri_puntata(tipo)
        
        if not numeri_da_puntare:
            messagebox.showwarning("Attenzione", "Nessun numero da puntare!")
            return

        # Disabilita pulsanti durante la puntata
        for btn in [self.btn_punta_normale, self.btn_punta_convergenti, self.btn_punta_solo_convergenti]:
            btn.config(state=tk.DISABLED)
        
        self.status_label.config(text=f"Esecuzione puntata {tipo}...")
        
        # Esegui in un thread per non bloccare l'interfaccia
        threading.Thread(target=self._esegui_puntate, args=(numeri_da_puntare, tipo)).start()

    def _esegui_puntate(self, numeri, tipo):
        try:
            # Configurazione per massima velocità
            pyautogui.PAUSE = 0.02
            pyautogui.FAILSAFE = False
            
            # Pre-muove il mouse in un angolo per reset
            pyautogui.moveTo(10, 10, duration=0.05)
            
            # Esegue puntate ottimizzate
            for numero in numeri:
                pos = self.mappa_tavolo.get(numero)
                if pos:
                    pyautogui.moveTo(pos[0], pos[1], duration=0)
                    pyautogui.click()
                    time.sleep(0.01)  # Pausa minima per stabilità
            
            self.root.after(0, lambda: messagebox.showinfo(
                "Puntata completata", 
                f"Puntata {tipo} eseguita su {len(set(numeri))} numeri\n" +
                f"Totale puntate: {len(numeri)}"
            ))
            
        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror(
                "Errore", 
                f"Errore durante la puntata:\n{str(e)}"
            ))
            
        finally:
            pyautogui.FAILSAFE = True
            self.root.after(0, lambda: self.status_label.config(text="Pronto"))
            for btn in [self.btn_punta_normale, self.btn_punta_convergenti, self.btn_punta_solo_convergenti]:
                self.root.after(0, lambda b=btn: b.config(state=tk.NORMAL))

    def calcola_numeri_puntata(self, tipo):
        if not self.ultima_previsione:
            return []

        analisi = self.ultima_previsione['analisi']
        prediction = self.ultima_previsione['prediction']
        strong = self.ultima_previsione['strong_numbers']
        
        # Ottieni strategie selezionate dall'utente (escludendo 'Previsione' e 'Numeri Forti')
        strategie_attive = [name for name, var in self.analisi_vars.items() 
                          if var.get() and name in analisi]
        
        # 1. PUNTATA NORMALE: Solo numeri della previsione base
        if tipo == "normale":
            return list(set(prediction))
        
        # 2. PUNTA CONVERGENTI: Tutti i numeri delle strategie selezionate (con duplicati)
        elif tipo == "convergenti":
            numeri_da_puntare = []
            if 'Previsione' in self.analisi_vars and self.analisi_vars['Previsione'].get():
                numeri_da_puntare.extend(prediction)
            if 'Numeri Forti' in self.analisi_vars and self.analisi_vars['Numeri Forti'].get():
                numeri_da_puntare.extend(strong)
            for strategia in strategie_attive:
                numeri_da_puntare.extend(analisi[strategia])
            return numeri_da_puntare
        
        # 3. SOLO CONVERGENTI: Numeri presenti in ALMENO 2 strategie diverse
        elif tipo == "solo_convergenti":
            conteggio = Counter()
            
            # Conta nelle strategie attive
            for strategia in strategie_attive:
                conteggio.update(analisi[strategia])
            
            # Considera anche 'Previsione' e 'Numeri Forti' se selezionati
            if 'Previsione' in self.analisi_vars and self.analisi_vars['Previsione'].get():
                conteggio.update(prediction)
            if 'Numeri Forti' in self.analisi_vars and self.analisi_vars['Numeri Forti'].get():
                conteggio.update(strong)
            
            # Filtra i numeri con almeno 2 occorrenze
            return [num for num, count in conteggio.items() if count >= 2]
        
        return []
    # ===== METODI ORIGINALI =====
    def reset_colori(self):
        for n, btn in self.buttons.items():
            bg = self.colori[n]
            fg = "black" if bg == "#FF0000" else "white"
            btn.config(bg=bg, fg=fg)
        self.btn_0.config(bg="#008000", fg="white")

    def aggiungi_spin(self, numero):
        if len(self.ultimi_spin) >= 1000:
            self.ultimi_spin.pop(0)
        self.ultimi_spin.append(numero)
        self.aggiorna_spin_labels()
        self.aggiorna_evidenziazione()

    def aggiorna_spin_labels(self):
        for i in range(13):
            idx = len(self.ultimi_spin) - 1 - i
            self.spin_labels[i].config(text=str(self.ultimi_spin[idx]) if idx >= 0 else "")

    def clear_results(self):
        for name in self.result_frames:
            if "_label" in name:
                self.result_frames[name].config(text="")
        self.reset_colori()

    def reset_all(self):
        self.ultimi_spin = []
        self.ultima_previsione = None
        self.clear_results()
        self.aggiorna_spin_labels()

    def annulla_ultimo(self):
        if self.ultimi_spin:
            self.ultimi_spin.pop()
            self.aggiorna_spin_labels()
            self.aggiorna_evidenziazione()

    def carica_file(self):
        path = filedialog.askopenfilename(filetypes=[("Text Files", "*.txt")])
        if not path:
            return
        
        try:
            with open(path, 'r') as f:
                numeri = [int(line.strip()) for line in f if line.strip().isdigit() and 0 <= int(line.strip()) <= 36]
            
            if not numeri:
                messagebox.showwarning("Attenzione", "Nessun numero valido trovato nel file")
                return
                
            self.reset_all()
            for n in numeri:
                self.aggiungi_spin(n)
            
            messagebox.showinfo("Successo", f"Caricati {len(numeri)} numeri validi")
        except Exception as e:
            messagebox.showerror("Errore", f"Errore nel caricamento:\n{str(e)}")

    def evidenzia_numeri(self, numeri, colore):
        for n in numeri:
            if n == 0:
                self.btn_0.config(bg=colore, fg="black")
            elif n in self.buttons:
                self.buttons[n].config(bg=colore, fg="black")

    def aggiorna_evidenziazione(self):
        if not self.ultima_previsione:
            return
        
        self.reset_colori()
        
        for name in self.analisi_vars:
            if self.analisi_vars[name].get():
                if name == 'Previsione':
                    nums = self.ultima_previsione['prediction']
                elif name == 'Numeri Forti':
                    nums = self.ultima_previsione['strong_numbers']
                else:
                    nums = self.ultima_previsione['analisi'].get(name, [])
                
                self.evidenzia_numeri(nums, self.COLORI_ANALISI[name])

    def mostra_previsione(self):
        if len(self.ultimi_spin) < 180:
            messagebox.showwarning("Attenzione", "Servono almeno 180 numeri per l'analisi")
            return
        
        try:
            strategia = self.strategie[self.strategia_selezionata.get()]
            self.ultima_previsione = strategia(self.ultimi_spin)
            
            for name in self.result_frames:
                if "_label" in name:
                    clean_name = name.replace("_label", "")
                    if clean_name == 'Previsione':
                        nums = self.ultima_previsione['prediction']
                    elif clean_name == 'Numeri Forti':
                        nums = self.ultima_previsione['strong_numbers']
                    else:
                        nums = self.ultima_previsione['analisi'].get(clean_name, [])
                    
                    self.result_frames[name].config(text=", ".join(map(str, nums)))
            
            self.aggiorna_evidenziazione()
            
            # Abilita pulsanti puntata dopo l'analisi
            if len(self.mappa_tavolo) >= 37:
                for btn in [self.btn_punta_normale, self.btn_punta_convergenti, self.btn_punta_solo_convergenti]:
                    btn.config(state=tk.NORMAL)
                    
        except Exception as e:
            messagebox.showerror("Errore", f"Errore durante l'analisi:\n{str(e)}")

if __name__ == "__main__":
    root = tk.Tk()
    app = RouletteApp(root)
    root.mainloop()