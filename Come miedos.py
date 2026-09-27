import math
import random
import time
import tkinter as tk

# Sonidos simples (solo Windows); en otros sistemas se ignoran sin problema
try:
    import winsound

    def sonido(alias):
        winsound.PlaySound(alias, winsound.SND_ALIAS | winsound.SND_ASYNC)
except ImportError:
    def sonido(alias):
        pass

# ---------------- Configuración ----------------
ANCHO, ALTO = 700, 500
VELOCIDAD = 5          # píxeles por fotograma
TICK_MS = 16           # ~60 fps
DURACION = 60          # segundos de partida
NUM_MURCIELAGOS = 3

COLOR_FONDO = "#120a24"
NARANJA = "#ff8c1a"
MORADO = "#b9a3ff"

EMOJI = "Segoe UI Emoji"
FUENTE_JUGADOR = (EMOJI, 34)
FUENTE_ITEM = (EMOJI, 32)


class Juego:
    def __init__(self, root):
        self.root = root
        root.title("🎃 Halloween Party 🎃")
        root.geometry("700x620")
        root.resizable(False, False)
        root.configure(bg=COLOR_FONDO)

        self.canvas = tk.Canvas(root, width=ANCHO, height=ALTO,
                                bg=COLOR_FONDO, highlightthickness=0)
        self.canvas.pack()

        self.teclas = set()
        self.jugando = False
        self.record = 0
        self.puntos = 0

        self.dibujar_fondo()
        self.crear_hud()
        self.crear_botones()

        root.bind("<KeyPress>", self.tecla_abajo)
        root.bind("<KeyRelease>", self.tecla_arriba)

        self.mostrar_inicio()

    # ---------------- Interfaz ----------------
    def dibujar_fondo(self):
        c = self.canvas
        for _ in range(70):
            x, y = random.randint(0, ANCHO), random.randint(0, ALTO)
            r = random.choice([1, 1, 2])
            c.create_oval(x - r, y - r, x + r, y + r,
                          fill=random.choice(["#ffffff", MORADO, "#ffd9a0"]),
                          outline="")
        c.create_text(600, 115, text="🌕", font=(EMOJI, 64))

    def crear_hud(self):
        c = self.canvas
        self.hud_puntos = c.create_text(15, 12, anchor="nw", fill=NARANJA,
                                        font=("Georgia", 16, "bold"),
                                        text="🎃 Puntos: 0")
        self.hud_tiempo = c.create_text(ANCHO // 2, 12, anchor="n", fill="white",
                                        font=("Georgia", 16, "bold"),
                                        text=f"⏳ {DURACION}")
        self.hud_record = c.create_text(ANCHO - 15, 12, anchor="ne", fill=MORADO,
                                        font=("Georgia", 16, "bold"),
                                        text="🏆 Récord: 0")

    def crear_botones(self):
        marco = tk.Frame(self.root, bg=COLOR_FONDO)
        marco.pack(expand=True)
        cfg = dict(font=(EMOJI, 20), width=3, bg="#2a1650", fg="white",
                   activebackground=NARANJA, relief="flat", bd=0)
        botones = [("⬆", "arr", 0, 1), ("⬅", "izq", 1, 0),
                   ("⬇", "abj", 1, 1), ("➡", "der", 1, 2)]
        for texto, clave, fila, col in botones:
            b = tk.Button(marco, text=texto, **cfg)
            b.grid(row=fila, column=col, padx=3, pady=3)
            # Mantener pulsado = seguir moviéndose
            b.bind("<ButtonPress-1>", lambda e, k=clave: self.teclas.add(k))
            b.bind("<ButtonRelease-1>", lambda e, k=clave: self.teclas.discard(k))

    def pantalla(self, titulo, lineas):
        c = self.canvas
        c.delete("overlay")
        c.create_rectangle(90, 100, 610, 400, fill="#1b0f36",
                           outline=NARANJA, width=3, tags="overlay")
        c.create_text(350, 150, text=titulo, fill=NARANJA,
                      font=("Georgia", 28, "bold"), tags="overlay")
        y = 205
        for linea in lineas:
            c.create_text(350, y, text=linea, fill="white",
                          font=("Arial", 13), tags="overlay")
            y += 30
        c.create_text(350, 370, text="Pulsa ESPACIO para jugar", fill=MORADO,
                      font=("Georgia", 14, "italic"), tags="overlay")

    def mostrar_inicio(self):
        self.pantalla("🎃 HALLOWEEN PARTY 🎃", [
            "Come demonios 😈  →  +100",
            "Atrapa el fantasma 👻 (aparece poco)  →  +200",
            "Esquiva los murciélagos 🦇  →  -50",
            "Muévete con las flechas, WASD o los botones",
        ])

    # ---------------- Entrada ----------------
    MAPA = {"left": "izq", "a": "izq", "right": "der", "d": "der",
            "up": "arr", "w": "arr", "down": "abj", "s": "abj"}

    def tecla_abajo(self, e):
        k = e.keysym.lower()
        if k in self.MAPA:
            self.teclas.add(self.MAPA[k])
        elif k in ("space", "return") and not self.jugando:
            self.iniciar()

    def tecla_arriba(self, e):
        k = e.keysym.lower()
        if k in self.MAPA:
            self.teclas.discard(self.MAPA[k])

    # ---------------- Partida ----------------
    def iniciar(self):
        c = self.canvas
        c.delete("overlay")
        c.delete("entidad")
        ahora = time.monotonic()

        self.puntos = 0
        self.jugando = True
        self.fin = ahora + DURACION
        self.invulnerable_hasta = 0
        self.px, self.py = ANCHO / 2, ALTO / 2

        self.jugador = c.create_text(self.px, self.py, text="🎃",
                                     font=FUENTE_JUGADOR, tags="entidad")
        self.demonio = c.create_text(0, 0, text="😈", font=FUENTE_ITEM,
                                     tags="entidad")
        self.recolocar_demonio(ahora)

        self.fantasma = None
        self.fantasma_expira = 0
        self.prox_fantasma = ahora + random.uniform(4, 8)

        self.murcielagos = [self.crear_murcielago() for _ in range(NUM_MURCIELAGOS)]

        self.actualizar_hud(ahora)
        self.bucle()

    def bucle(self):
        if not self.jugando:
            return
        ahora = time.monotonic()
        if ahora >= self.fin:
            self.terminar()
            return
        self.mover_jugador(ahora)
        self.mover_murcielagos(ahora)
        self.gestionar_demonio(ahora)
        self.gestionar_fantasma(ahora)
        self.actualizar_hud(ahora)
        self.root.after(TICK_MS, self.bucle)

    def terminar(self):
        self.jugando = False
        self.teclas.clear()
        nuevo_record = self.puntos > self.record
        if nuevo_record:
            self.record = self.puntos
        self.actualizar_hud(self.fin)

        if self.puntos < 300:
            rango = "Aprendiz de brujo 🧙"
        elif self.puntos < 800:
            rango = "Cazador de demonios 😈"
        else:
            rango = "¡Rey del Halloween! 👑"

        lineas = [f"Puntos: {self.puntos}", rango]
        if nuevo_record:
            lineas.append("🏆 ¡Nuevo récord! 🏆")
        self.pantalla("💀 FIN DEL JUEGO 💀", lineas)

    # ---------------- Jugador ----------------
    def mover_jugador(self, ahora):
        dx = ("der" in self.teclas) - ("izq" in self.teclas)
        dy = ("abj" in self.teclas) - ("arr" in self.teclas)
        factor = 0.707 if dx and dy else 1
        self.px = min(max(self.px + dx * VELOCIDAD * factor, 25), ANCHO - 25)
        self.py = min(max(self.py + dy * VELOCIDAD * factor, 55), ALTO - 25)
        self.canvas.coords(self.jugador, self.px, self.py)

        # Parpadeo tras un golpe
        if ahora < self.invulnerable_hasta:
            oculto = int(ahora * 12) % 2 == 0
            self.canvas.itemconfigure(self.jugador,
                                      state="hidden" if oculto else "normal")
        else:
            self.canvas.itemconfigure(self.jugador, state="normal")

    def choca(self, x, y, radio=38):
        return math.hypot(self.px - x, self.py - y) < radio

    def sumar(self, cantidad, x, y):
        self.puntos = max(0, self.puntos + cantidad)
        color = "#7dff7d" if cantidad > 0 else "#ff5c5c"
        self.popup(x, y, f"{cantidad:+d}", color)
        sonido("SystemAsterisk" if cantidad > 0 else "SystemHand")

    def popup(self, x, y, texto, color):
        pid = self.canvas.create_text(x, y - 30, text=texto, fill=color,
                                      font=("Arial", 18, "bold"), tags="popup")
        self._animar(pid, 0)

    def _animar(self, pid, paso):
        if paso >= 20:
            self.canvas.delete(pid)
            return
        self.canvas.move(pid, 0, -2)
        self.root.after(30, self._animar, pid, paso + 1)

    # ---------------- Demonio ----------------
    def posicion_libre(self, distancia_min=140):
        while True:
            x, y = random.randint(40, ANCHO - 40), random.randint(70, ALTO - 40)
            if math.hypot(x - self.px, y - self.py) > distancia_min:
                return x, y

    def recolocar_demonio(self, ahora):
        x, y = self.posicion_libre()
        self.canvas.coords(self.demonio, x, y)
        self.prox_demonio = ahora + 3  # cambia de sitio cada 3 s

    def gestionar_demonio(self, ahora):
        x, y = self.canvas.coords(self.demonio)
        if self.choca(x, y):
            self.sumar(100, x, y)
            self.recolocar_demonio(ahora)
        elif ahora >= self.prox_demonio:
            self.recolocar_demonio(ahora)

    # ---------------- Fantasma bonus ----------------
    def gestionar_fantasma(self, ahora):
        c = self.canvas
        if self.fantasma is None:
            if ahora >= self.prox_fantasma:
                x, y = self.posicion_libre(200)
                self.fantasma = c.create_text(x, y, text="👻", font=FUENTE_ITEM,
                                              tags="entidad")
                self.fantasma_expira = ahora + 4
            return

        x, y = c.coords(self.fantasma)
        # Flota suavemente
        c.coords(self.fantasma, x, y + math.sin(ahora * 6) * 0.8)
        if self.choca(x, y):
            self.sumar(200, x, y)
            self.quitar_fantasma(ahora)
        elif ahora >= self.fantasma_expira:
            self.quitar_fantasma(ahora)

    def quitar_fantasma(self, ahora):
        self.canvas.delete(self.fantasma)
        self.fantasma = None
        self.prox_fantasma = ahora + random.uniform(6, 12)

    # ---------------- Murciélagos ----------------
    def crear_murcielago(self):
        direccion = random.choice([-1, 1])
        x = -30 if direccion == 1 else ANCHO + 30
        y0 = random.randint(90, ALTO - 60)
        item = self.canvas.create_text(x, y0, text="🦇", font=FUENTE_ITEM,
                                       tags="entidad")
        return {"id": item, "x": x, "y0": y0, "dir": direccion,
                "vel": random.uniform(2.0, 3.8),
                "fase": random.uniform(0, 6.28)}

    def mover_murcielagos(self, ahora):
        for m in self.murcielagos:
            m["x"] += m["dir"] * m["vel"]
            y = m["y0"] + 35 * math.sin(m["x"] / 45 + m["fase"])
            self.canvas.coords(m["id"], m["x"], y)

            fuera = m["x"] < -40 or m["x"] > ANCHO + 40
            if fuera:
                m["dir"] = random.choice([-1, 1])
                m["x"] = -30 if m["dir"] == 1 else ANCHO + 30
                m["y0"] = random.randint(90, ALTO - 60)
                m["vel"] = random.uniform(2.0, 3.8)
                continue

            if ahora >= self.invulnerable_hasta and self.choca(m["x"], y, 34):
                self.sumar(-50, self.px, self.py)
                self.invulnerable_hasta = ahora + 1.2

    # ---------------- HUD ----------------
    def actualizar_hud(self, ahora):
        c = self.canvas
        restante = max(0, math.ceil(self.fin - ahora))
        c.itemconfigure(self.hud_puntos, text=f"🎃 Puntos: {self.puntos}")
        c.itemconfigure(self.hud_record, text=f"🏆 Récord: {self.record}")
        c.itemconfigure(self.hud_tiempo, text=f"⏳ {restante}",
                        fill="#ff5c5c" if restante <= 10 else "white")


if __name__ == "__main__":
    ventana = tk.Tk()
    Juego(ventana)
    ventana.mainloop()