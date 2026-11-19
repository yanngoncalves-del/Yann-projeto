import os
import sys
import math
import time
import random
import subprocess
from datetime import datetime
from flask import Flask, render_template, request

# ==========================================
# SITUAÇÃO DE APRENDIZAGEM (SA)
# Projeto: Streaming Horror 3D (Web + Pygame)
# ==========================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
RAIZ_PROJETOS = os.path.abspath(os.path.join(BASE_DIR, "..", ".."))

# Vasculha TODAS as pastas e subpastas dentro de Projetos até achar o index.html
PASTA_WEB = BASE_DIR
for raiz, pastas, arquivos in os.walk(RAIZ_PROJETOS):
    for arq in arquivos:
        if arq.lower() == "index.html":
            PASTA_WEB = raiz
            break
    if PASTA_WEB != BASE_DIR:
        break

print(">>> PASTA ENCONTRADA:", PASTA_WEB)
ARQUIVO_USUARIOS = os.path.join(BASE_DIR, "usuarios.txt")
app = Flask(__name__, template_folder=PASTA_WEB, static_folder=PASTA_WEB, static_url_path="")

ARQUIVO_USUARIOS = os.path.join(BASE_DIR, "usuarios.txt")

# Diz ao Flask para usar exatamente a PASTA_WEB como pasta de HTML e CSS
app = Flask(__name__, template_folder=PASTA_WEB, static_folder=PASTA_WEB, static_url_path="")


def carregar_usuarios():
    usuarios = {}
    if not os.path.exists(ARQUIVO_USUARIOS):
        return usuarios
    with open(ARQUIVO_USUARIOS, "r", encoding="utf-8") as f:
        for linha in f:
            if ";" in linha.strip():
                email, senha = linha.strip().split(";", 1)
                usuarios[email] = senha
    return usuarios


def salvar_usuario(email, senha):
    with open(ARQUIVO_USUARIOS, "a", encoding="utf-8") as f:
        f.write(f"{email};{senha}\n")


@app.route("/", methods=["GET", "POST"])
def pagina_inicial():
    mensagem = None
    tipo_msg = ""
    canal = None

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        senha = request.form.get("senha", "").strip()
        acao = request.form.get("acao")
        usuarios = carregar_usuarios()

        if acao == "login":
            if email in usuarios and usuarios[email] == senha:
                canal = email.split("@")[0]
            else:
                mensagem = "E-mail ou senha incorretos!"
                tipo_msg = "erro"

        elif acao == "cadastro":
            if "@" not in email or "." not in email:
                mensagem = "Digite um e-mail válido."
                tipo_msg = "erro"
            elif email in usuarios:
                mensagem = "Este e-mail já está cadastrado!"
                tipo_msg = "erro"
            elif len(senha) < 4:
                mensagem = "A senha deve ter no mínimo 4 dígitos."
                tipo_msg = "erro"
            else:
                salvar_usuario(email, senha)
                mensagem = "Conta criada com sucesso! Agora clique em Entrar."
                tipo_msg = "sucesso"

    return render_template("index.html", mensagem=mensagem, tipo_msg=tipo_msg, canal=canal)


@app.route("/jogar", methods=["POST"])
def iniciar_jogo():
    canal = request.form.get("canal", "Streamer")
    subprocess.Popen([sys.executable, __file__, "--jogar", canal])
    return render_template(
        "index.html",
        mensagem="Janela 3D aberta! Confira a barra de tarefas se ela abrir atrás do navegador.",
        tipo_msg="sucesso",
        canal=canal
    )


# ==========================================
# MÓDULO 2: MOTOR 3D + 4 AMEAÇAS + CAMA + ALVOS
# ==========================================

LARGURA = 900
ALTURA = 620
FPS = 60

FOV = math.pi / 3
NUM_RAIOS = 225
DELTA_ANGULO = FOV / NUM_RAIOS
PROFUNDIDADE_MAX = 16

# Duração total da noite: 12 minutos = 720 segundos (00:00 AM até 06:00 AM)
DURACAO_NOITE_SEGUNDOS = 720.0

# Mapa do Quarto (8x8)
# 0 = Chão livre | 1 = Parede | 2 = Porta (Direita) | 3 = Janela ao lado do PC (Topo-Esquerda)
MAPA_QUARTO = [
    [1, 1, 3, 1, 1, 1, 1, 1],
    [1, 0, 0, 0, 0, 0, 0, 1],
    [1, 0, 0, 0, 0, 0, 0, 1],
    [1, 0, 0, 0, 0, 0, 0, 2],
    [1, 0, 0, 0, 0, 0, 0, 1],
    [1, 0, 0, 0, 0, 0, 0, 1],
    [1, 0, 0, 0, 0, 0, 0, 1],
    [1, 1, 1, 1, 1, 1, 1, 1],
]


class JogoStreaming3D:
    def __init__(self, nome_canal):
        import pygame
        self.pg = pygame
        self.pg.init()
        self.tela = self.pg.display.set_mode((LARGURA, ALTURA))
        self.pg.display.set_caption(f"Live Horror 3D - Canal: {nome_canal}")
        self.clock = self.pg.time.Clock()

        # Fontes
        self.fonte_chat = self.pg.font.SysFont("Consolas", 14)
        self.fonte_pequena = self.pg.font.SysFont("Consolas", 16)
        self.fonte_hud = self.pg.font.SysFont("Consolas", 18, bold=True)
        self.fonte_aviso = self.pg.font.SysFont("Consolas", 22, bold=True)
        self.fonte_grande = self.pg.font.SysFont("Consolas", 30, bold=True)
        self.fonte_gigante = self.pg.font.SysFont("Consolas", 48, bold=True)

        # Posição inicial do jogador
        self.px = 4.0
        self.py = 4.6
        self.angulo = -math.pi / 2

        # Coordenadas dos móveis 3D no quarto (com colisão!)
        self.mesa_pos = (4.2, 2.0)       # Mesa com PC (Norte, à direita da janela)
        self.cadeira_pos = (4.2, 2.85)   # Cadeira Gamer
        self.cama_pos = (1.55, 2.7)      # Cama encostada na parede esquerda (esconderijo!)
        self.armario_pos = (1.45, 4.3)   # Mini armário de 1 gaveta ao lado da cama

        # Sprites 3D
        self.sprite_mesa_pc_ligado = self.criar_sprite_mesa_pc(ligado=True)
        self.sprite_mesa_pc_desligado = self.criar_sprite_mesa_pc(ligado=False)
        self.sprite_cadeira = self.criar_sprite_cadeira()
        self.sprite_cama = self.criar_sprite_cama()
        self.sprite_armario = self.criar_sprite_armario()
        self.sprite_fantasma = self.criar_sprite_fantasma()

        # Estados: "QUARTO_3D", "MENU_PC", "NO_PC", "OLHO_MAGICO", "JANELA", "DEBAIXO_CAMA", "RELATORIO", "VITORIA", "GAME_OVER"
        self.estado = "QUARTO_3D"
        self.motivo_gameover = ""
        self.tipo_gameover = "MONSTRO"

        # Cronômetro de Sobrevivência (00:00 AM -> 06:00 AM em 12 minutos)
        self.tempo_sobrevivido = 0.0

        # Estado do Computador e Silêncio (PC + Lanterna desligados)
        self.pc_ligado = True
        self.tempo_silencio_total = 0.0

        # Estado da Janela e Hater (com círculos vermelhos clicáveis!)
        self.janela_aberta = False
        self.hater_na_janela = False
        self.vida_hater = 6
        self.alvo_hater_pos = (LARGURA // 2, ALTURA // 2)
        self.alvo_hater_raio = 28
        self.tempo_limite_hater = 0
        self.animacao_soco = 0.0

        # Lanterna e Bateria
        self.lanterna_ligada = True
        self.bateria = 100.0
        self.aviso_status_timer = 0.0
        self.texto_aviso_status = ""

        # Dados do Canal e Pontuação
        self.nome_canal = nome_canal
        self.total_inscritos = 0
        self.total_likes = 0
        self.total_dislikes = 0
        self.ameacas_sobrevividas = 0

        # Dados da Live Atual
        self.em_live = False
        self.likes_live = 0
        self.dislikes_live = 0
        self.inscritos_live = 0
        self.fala_personagem = "E aí galera, começando a live!"
        self.dados_relatorio = {}

        # Sistema de Chat Contínuo
        self.historico_chat = [
            ("Sistema", "Sobreviva até as 06:00 AM! Ligue a live no PC.", (150, 200, 255))
        ]
        self.timer_bot_chat = 0.0

        # Digitação
        self.digitando_fala = False
        self.texto_digitado = ""

        # Ameaça 1: Sombra na Porta
        self.ameaca_porta = False
        self.tempo_limite_porta = 0
        self.tempo_encarando = 0.0
        self.tempo_necessario_encarar = 5.0

        # Ameaça 2: Fantasma no Quarto (silencioso!)
        self.fantasma_ativo = False
        self.fantasma_pos = (5.5, 5.5)
        self.tempo_limite_fantasma = 0
        self.luz_no_fantasma = 0.0

        # Ameaça 3: Mãe (Fase 1: Na Porta | Fase 2: Entrou no Quarto -> Esconder debaixo da cama!)
        self.mae_na_porta = False
        self.tempo_limite_mae_porta = 0
        self.mae_no_quarto = False
        self.tempo_limite_esconder = 0
        self.tempo_debaixo_cama = 0.0

        self.acoes_na_live = 0

    # ==========================================
    # GERADOR DE SPRITES DOS MÓVEIS E FANTASMA
    # ==========================================

    def criar_sprite_mesa_pc(self, ligado=True):
        surf = self.pg.Surface((260, 260), self.pg.SRCALPHA)
        self.pg.draw.rect(surf, (45, 45, 52), (30, 145, 14, 115))
        self.pg.draw.rect(surf, (45, 45, 52), (216, 145, 14, 115))
        self.pg.draw.rect(surf, (115, 72, 42), (18, 132, 224, 16), border_radius=3)
        self.pg.draw.rect(surf, (80, 48, 25), (18, 132, 224, 16), 2, border_radius=3)

        self.pg.draw.rect(surf, (25, 28, 35), (185, 62, 42, 70), border_radius=3)
        if ligado:
            self.pg.draw.rect(surf, (0, 220, 255), (190, 68, 4, 58))

        self.pg.draw.rect(surf, (35, 35, 40), (105, 126, 40, 6))
        self.pg.draw.rect(surf, (35, 35, 40), (121, 108, 8, 18))

        self.pg.draw.rect(surf, (20, 22, 28), (68, 44, 114, 68), border_radius=4)
        if ligado:
            self.pg.draw.rect(surf, (25, 110, 175), (73, 49, 104, 58))
            self.pg.draw.rect(surf, (15, 20, 30), (77, 53, 62, 36))
            self.pg.draw.circle(surf, (230, 190, 150), (108, 68), 8)
            self.pg.draw.rect(surf, (255, 50, 50), (155, 53, 18, 8))
        else:
            self.pg.draw.rect(surf, (8, 9, 12), (73, 49, 104, 58))

        self.pg.draw.rect(surf, (15, 15, 15), (117, 38, 16, 6))
        if ligado:
            self.pg.draw.circle(surf, (0, 255, 120), (125, 41), 2)

        self.pg.draw.rect(surf, (30, 32, 38), (85, 127, 65, 5))
        if ligado:
            self.pg.draw.rect(surf, (0, 200, 255), (87, 128, 61, 2))
        self.pg.draw.rect(surf, (35, 35, 40), (158, 127, 12, 5))
        return surf

    def criar_sprite_cadeira(self):
        surf = self.pg.Surface((180, 220), self.pg.SRCALPHA)
        self.pg.draw.line(surf, (40, 40, 45), (50, 212), (130, 212), 5)
        self.pg.draw.circle(surf, (25, 25, 28), (50, 214), 5)
        self.pg.draw.circle(surf, (25, 25, 28), (90, 215), 5)
        self.pg.draw.circle(surf, (25, 25, 28), (130, 214), 5)
        self.pg.draw.rect(surf, (55, 55, 60), (85, 175, 10, 37))
        self.pg.draw.rect(surf, (30, 32, 38), (52, 162, 76, 14), border_radius=4)
        self.pg.draw.rect(surf, (45, 45, 50), (46, 138, 8, 28))
        self.pg.draw.rect(surf, (45, 45, 50), (126, 138, 8, 28))
        self.pg.draw.polygon(surf, (28, 30, 36), [(58, 162), (122, 162), (114, 72), (66, 72)])
        self.pg.draw.polygon(surf, (140, 35, 45), [(66, 155), (74, 155), (72, 80), (68, 80)])
        self.pg.draw.polygon(surf, (140, 35, 45), [(106, 155), (114, 155), (112, 80), (108, 80)])
        self.pg.draw.rect(surf, (160, 40, 50), (76, 82, 28, 14), border_radius=4)
        return surf

    def criar_sprite_cama(self):
        surf = self.pg.Surface((260, 260), self.pg.SRCALPHA)
        self.pg.draw.rect(surf, (85, 50, 28), (22, 195, 16, 65))
        self.pg.draw.rect(surf, (85, 50, 28), (222, 195, 16, 65))
        self.pg.draw.rect(surf, (12, 12, 16), (38, 214, 184, 46))
        self.pg.draw.rect(surf, (95, 56, 32), (16, 115, 22, 110), border_radius=3)
        self.pg.draw.rect(surf, (105, 62, 35), (20, 192, 220, 22))
        self.pg.draw.rect(surf, (215, 215, 225), (34, 168, 204, 24), border_radius=4)
        self.pg.draw.rect(surf, (45, 65, 110), (85, 166, 155, 28), border_radius=4)
        self.pg.draw.ellipse(surf, (245, 245, 250), (38, 154, 48, 18))
        return surf

    def criar_sprite_armario(self):
        surf = self.pg.Surface((200, 220), self.pg.SRCALPHA)
        self.pg.draw.rect(surf, (110, 68, 38), (45, 115, 110, 95), border_radius=4)
        self.pg.draw.rect(surf, (70, 42, 22), (45, 115, 110, 95), 3, border_radius=4)
        self.pg.draw.rect(surf, (130, 82, 46), (38, 108, 124, 10), border_radius=2)
        self.pg.draw.rect(surf, (65, 38, 20), (50, 210, 12, 10))
        self.pg.draw.rect(surf, (65, 38, 20), (138, 210, 12, 10))
        self.pg.draw.rect(surf, (92, 55, 30), (54, 124, 92, 36), border_radius=3)
        self.pg.draw.rect(surf, (55, 32, 16), (54, 124, 92, 36), 2, border_radius=3)
        self.pg.draw.rect(surf, (220, 195, 90), (90, 139, 20, 6), border_radius=2)
        self.pg.draw.rect(surf, (48, 28, 15), (56, 168, 88, 34))
        return surf

    def criar_sprite_fantasma(self):
        surf = self.pg.Surface((220, 260), self.pg.SRCALPHA)
        self.pg.draw.ellipse(surf, (180, 220, 255, 45), (35, 20, 150, 210))
        pontos_corpo = [
            (110, 30), (155, 65), (165, 145), (150, 225),
            (130, 195), (110, 230), (90, 195), (70, 225),
            (55, 145), (65, 65)
        ]
        self.pg.draw.polygon(surf, (210, 230, 245, 145), pontos_corpo)
        self.pg.draw.ellipse(surf, (15, 18, 25, 220), (82, 75, 18, 26))
        self.pg.draw.ellipse(surf, (15, 18, 25, 220), (120, 75, 18, 26))
        self.pg.draw.circle(surf, (255, 255, 255, 230), (91, 86), 3)
        self.pg.draw.circle(surf, (255, 255, 255, 230), (129, 86), 3)
        self.pg.draw.ellipse(surf, (15, 18, 25, 220), (98, 115, 24, 34))
        return surf

    # ==========================================
    # RELÓGIO DA NOITE (00:00 AM -> 06:00 AM) E PONTUAÇÃO
    # ==========================================

    def obter_horario_formatado(self):
        progresso = min(1.0, self.tempo_sobrevivido / DURACAO_NOITE_SEGUNDOS)
        minutos_totais_jogo = int(progresso * 360)
        horas = minutos_totais_jogo // 60
        minutos = minutos_totais_jogo % 60
        return f"{horas:02d}:{minutos:02d} AM"

    def calcular_pontuacao_final(self):
        subs_atuais = self.total_inscritos + (self.inscritos_live if self.em_live else 0)
        likes_atuais = self.total_likes + (self.likes_live if self.em_live else 0)
        dislikes_atuais = self.total_dislikes + (self.dislikes_live if self.em_live else 0)

        pontos = (
            (subs_atuais * 50)
            + (likes_atuais * 15)
            + (self.ameacas_sobrevividas * 250)
            + int(self.bateria * 5)
            - (dislikes_atuais * 20)
        )
        return max(0, pontos), subs_atuais, likes_atuais, dislikes_atuais

    # ==========================================
    # SISTEMA DE CHAT VIVO (IA SIMULADA)
    # ==========================================

    def adicionar_mensagem_chat(self, autor, texto, cor=(210, 210, 210)):
        self.historico_chat.append((autor, texto, cor))
        if len(self.historico_chat) > 11:
            self.historico_chat.pop(0)

    def gerar_mensagem_ia_chat(self, contexto="NORMAL"):
        nicks = [
            "Lucas_Gameplay", "AnaClara_BR", "Pedro_09", "MestreDoCodigo",
            "Gabi_Live", "Shadow_X", "rafael_santos", "Julia_TV", "BielZera"
        ]
        autor = random.choice(nicks)
        cor_nick = random.choice([(100, 220, 255), (130, 255, 160), (255, 200, 110), (210, 150, 255)])

        if contexto == "NORMAL":
            falas = [
                "salveee mano, manda um alô!",
                "essa live de madrugada é boa demais kkk",
                "faltam poucas horas pras 6 da manhã!",
                "o áudio tá limpo demais",
                "cheguei agora, já deixei o like!",
                "alguém mais assistindo antes de dormir?",
                "kkkkk boa",
                "não fala muito alto senão tua mãe acorda kkk",
                "tô acompanhando desde meia-noite!"
            ]
            self.adicionar_mensagem_chat(autor, random.choice(falas), cor_nick)

        elif contexto == "REACAO_FALA":
            falas = [
                "concordo demais com isso kkkk",
                "fala mesmo!!",
                "kkkkkkkkk verdade",
                "manda salve pra mim também!",
                "boa! continua assim"
            ]
            self.adicionar_mensagem_chat(autor, random.choice(falas), cor_nick)

        elif contexto == "TERROR_PORTA":
            sussurros = [
                ("000000", "ja olhou a porta?"),
                ("DESCONHECIDO", "tem alguém parado na sua porta..."),
                ("sem_nome", "ei... olha pelo olho mágico da porta"),
                ("...", "não ignora o barulho na porta")
            ]
            nick_estranho, msg_estranha = random.choice(sussurros)
            self.adicionar_mensagem_chat(nick_estranho, msg_estranha, (195, 175, 175))

        elif contexto == "AVISO_MAE":
            avisos = [
                ("MÃE (Corredor)", "EI! FAZ MENOS BARULHO E APAGA ESSA LUZ!"),
                ("MÃE (Na Porta)", "DESLIGA ESSE PC E ESSA LANTERNA AGORA!"),
                ("Lucas_Gameplay", "ih rapaz, tua mãe tá na porta! desliga o PC e a lanterna!")
            ]
            nick_m, msg_m = random.choice(avisos)
            self.adicionar_mensagem_chat(nick_m, msg_m, (255, 210, 130))

        elif contexto == "AVISO_HATER":
            avisos_hater = [
                ("Hater_Supremo", "ACHEI TEU ENDEREÇO KKKKK OLHA A JANELA!"),
                ("TROLL_99", "TÔ AQUI NA TUA JANELA SEU NOOB!"),
                ("Gabi_Live", "MANO TEM UM CARA BATENDO NO VIDRO DA TUA JANELA!!")
            ]
            nick_h, msg_h = random.choice(avisos_hater)
            self.adicionar_mensagem_chat(nick_h, msg_h, (255, 150, 90))

    # ==========================================
    # LÓGICA DA LIVE, ALVOS DO HATER E 4 AMEAÇAS
    # ==========================================

    def iniciar_nova_live(self):
        self.em_live = True
        self.likes_live = 0
        self.dislikes_live = 0
        self.inscritos_live = 0
        self.acoes_na_live = 0
        self.fala_personagem = "Salve chat! Estamos AO VIVO!"
        self.historico_chat.clear()
        self.adicionar_mensagem_chat("Sistema", "Transmissão iniciada!", (140, 140, 140))
        self.gerar_mensagem_ia_chat("NORMAL")

    def encerrar_live(self):
        self.em_live = False
        self.total_inscritos += self.inscritos_live
        self.total_likes += self.likes_live
        self.total_dislikes += self.dislikes_live

        self.dados_relatorio = {
            "data_hora": datetime.now().strftime("%d/%m/%Y às %H:%M:%S"),
            "inscritos": self.inscritos_live,
            "likes": self.likes_live,
            "dislikes": self.dislikes_live
        }
        self.estado = "RELATORIO"

    def gerar_novo_alvo_hater(self):
        cx = LARGURA // 2 + random.randint(-85, 85)
        cy = ALTURA // 2 + random.randint(-65, 110)
        self.alvo_hater_pos = (cx, cy)

    def spawnar_fantasma_silencioso(self):
        pontos_possiveis = [
            (2.2, 5.5), (5.8, 2.2), (5.8, 5.6),
            (2.8, 1.8), (6.0, 4.5), (3.2, 6.0)
        ]
        self.fantasma_pos = random.choice(pontos_possiveis)
        self.fantasma_ativo = True
        self.tempo_limite_fantasma = time.time() + 24
        self.luz_no_fantasma = 0.0

    def disparar_gatilho_ameacas(self):
        sem_ameaca = (
            not self.ameaca_porta
            and not self.fantasma_ativo
            and not self.mae_na_porta
            and not self.mae_no_quarto
            and not self.hater_na_janela
        )
        if sem_ameaca and self.acoes_na_live >= 2 and random.random() < 0.60:
            sorteio = random.choice(["SOMBRA_PORTA", "FANTASMA", "MAE", "HATER"])

            if sorteio == "SOMBRA_PORTA":
                self.ameaca_porta = True
                self.tempo_limite_porta = time.time() + 22
                self.gerar_mensagem_ia_chat("TERROR_PORTA")

            elif sorteio == "FANTASMA":
                self.spawnar_fantasma_silencioso()

            elif sorteio == "MAE":
                self.mae_na_porta = True
                self.tempo_silencio_total = 0.0
                self.tempo_limite_mae_porta = time.time() + 18
                self.gerar_mensagem_ia_chat("AVISO_MAE")

            elif sorteio == "HATER":
                self.hater_na_janela = True
                self.vida_hater = 6
                self.gerar_novo_alvo_hater()
                self.tempo_limite_hater = time.time() + 25
                self.gerar_mensagem_ia_chat("AVISO_HATER")

    def processar_acao_live(self, tipo, texto_fala=""):
        self.acoes_na_live += 1

        if tipo == "FALAR":
            if not texto_fala.strip():
                self.fala_personagem = "..."
                self.dislikes_live += 1
                self.adicionar_mensagem_chat("Pedro_09", "ficou mudo do nada? kkk", (255, 140, 140))
            else:
                self.fala_personagem = texto_fala.strip()
                palavras_ruins = ["chato", "cala a boca", "lixo", "odeio", "ruim", "sai"]
                if any(p in texto_fala.lower() for p in palavras_ruins):
                    perdidos = random.randint(2, 5)
                    self.dislikes_live += perdidos
                    self.adicionar_mensagem_chat("AnaClara_BR", "nossa pra que grosseria...", (255, 120, 120))
                else:
                    bonus = 2 if len(texto_fala) > 18 else 1
                    novos_likes = random.randint(2, 5) * bonus
                    novos_subs = random.randint(1, 3)
                    self.likes_live += novos_likes
                    self.inscritos_live += novos_subs
                    self.gerar_mensagem_ia_chat("REACAO_FALA")

        elif tipo == "JOGADA":
            self.fala_personagem = "OLHA ESSA JOGADA AGORA!!"
            if random.random() < 0.70:
                novos_likes = random.randint(8, 15)
                novos_subs = random.randint(3, 7)
                self.likes_live += novos_likes
                self.inscritos_live += novos_subs
                self.adicionar_mensagem_chat("Lucas_Gameplay", "CARACAAA QUE JOGADA INSANA!!", (100, 255, 140))
            else:
                novos_dislikes = random.randint(3, 7)
                self.dislikes_live += novos_dislikes
                self.fala_personagem = "Puts... deu tudo errado kkk"
                self.adicionar_mensagem_chat("BielZera", "KKKKKKKKKK pinou tudo", (255, 140, 140))

        elif tipo == "SILENCIO":
            self.fala_personagem = "*olhando para o monitor em silêncio*"
            self.likes_live += 1
            if random.random() < 0.4:
                self.dislikes_live += 1
                self.adicionar_mensagem_chat("Julia_TV", "fala alguma coisa mano...", (200, 200, 200))

        self.disparar_gatilho_ameacas()

    def mostrar_aviso_rapido(self, texto, duracao=2.8):
        self.texto_aviso_status = texto
        self.aviso_status_timer = duracao

    # ==========================================
    # MOVIMENTAÇÃO E COLISÃO COM MÓVEIS 3D
    # ==========================================

    def colidiu_com_moveis(self, nx, ny):
        if abs(nx - self.mesa_pos[0]) < 0.85 and abs(ny - self.mesa_pos[1]) < 0.42:
            return True
        if math.hypot(nx - self.cadeira_pos[0], ny - self.cadeira_pos[1]) < 0.36:
            return True
        if abs(nx - self.cama_pos[0]) < 0.55 and abs(ny - self.cama_pos[1]) < 0.85:
            return True
        if abs(nx - self.armario_pos[0]) < 0.42 and abs(ny - self.armario_pos[1]) < 0.42:
            return True
        return False

    def mover_jogador(self, dt):
        teclas = self.pg.key.get_pressed()
        vel_andar = 3.2 * dt
        vel_girar = 2.4 * dt

        if teclas[self.pg.K_LEFT]:
            self.angulo -= vel_girar
        if teclas[self.pg.K_RIGHT]:
            self.angulo += vel_girar

        dx, dy = 0, 0
        if teclas[self.pg.K_w]:
            dx += math.cos(self.angulo) * vel_andar
            dy += math.sin(self.angulo) * vel_andar
        if teclas[self.pg.K_s]:
            dx -= math.cos(self.angulo) * vel_andar
            dy -= math.sin(self.angulo) * vel_andar
        if teclas[self.pg.K_a]:
            dx += math.sin(self.angulo) * vel_andar
            dy -= math.cos(self.angulo) * vel_andar
        if teclas[self.pg.K_d]:
            dx -= math.sin(self.angulo) * vel_andar
            dy += math.cos(self.angulo) * vel_andar

        margem = 0.25
        novo_x = self.px + dx
        if MAPA_QUARTO[int(self.py)][int(novo_x + (margem if dx > 0 else -margem))] == 0:
            if not self.colidiu_com_moveis(novo_x, self.py):
                self.px = novo_x

        novo_y = self.py + dy
        if MAPA_QUARTO[int(novo_y + (margem if dy > 0 else -margem))][int(self.px)] == 0:
            if not self.colidiu_com_moveis(self.px, novo_y):
                self.py = novo_y

    def verificar_interacao_proxima(self):
        dist_pc = math.hypot(self.px - self.mesa_pos[0], self.py - self.mesa_pos[1])
        dist_cad = math.hypot(self.px - self.cadeira_pos[0], self.py - self.cadeira_pos[1])
        if dist_pc < 1.35 or dist_cad < 0.85:
            return "PC"

        dist_cama = math.hypot(self.px - self.cama_pos[0], self.py - self.cama_pos[1])
        if dist_cama < 1.35:
            return "CAMA"

        dist_armario = math.hypot(self.px - self.armario_pos[0], self.py - self.armario_pos[1])
        if dist_armario < 1.15:
            return "ARMARIO"

        check_x = int(self.px + math.cos(self.angulo) * 1.15)
        check_y = int(self.py + math.sin(self.angulo) * 1.15)
        if 0 <= check_y < 8 and 0 <= check_x < 8:
            bloco = MAPA_QUARTO[check_y][check_x]
            if bloco == 2:
                return "PORTA"
            elif bloco == 3:
                return "JANELA"

        return None

    # ==========================================
    # CÁLCULO DE ILUMINAÇÃO DA LANTERNA
    # ==========================================

    def calcular_fator_luz(self, angulo_alvo, distancia):
        luz_ambiente = max(0.05, 0.22 - (distancia * 0.025))

        if not self.lanterna_ligada or self.bateria <= 0:
            return luz_ambiente

        diff = angulo_alvo - self.angulo
        while diff > math.pi:
            diff -= 2 * math.pi
        while diff < -math.pi:
            diff += 2 * math.pi

        abertura_cone = 0.42
        if abs(diff) < abertura_cone:
            foco = 1.0 - (abs(diff) / abertura_cone)
            alcance = max(0.0, 1.0 - (distancia / 8.5))
            falha = random.uniform(0.4, 1.0) if self.bateria < 15 else 1.0
            luz_lanterna = (foco ** 1.3) * alcance * 1.15 * falha
            return min(1.0, luz_ambiente + luz_lanterna)

        return luz_ambiente

    # ==========================================
    # RENDERIZAÇÃO 3D (PAREDES, PORTA, JANELA E MÓVEIS)
    # ==========================================

    def renderizar_3d(self):
        fator_chao = 1.0 if (self.lanterna_ligada and self.bateria > 0) else 0.35
        self.tela.fill((int(16 * fator_chao), int(18 * fator_chao), int(24 * fator_chao)), (0, 0, LARGURA, ALTURA // 2))
        self.tela.fill((int(42 * fator_chao), int(32 * fator_chao), int(24 * fator_chao)), (0, ALTURA // 2, LARGURA, ALTURA // 2))

        z_buffer = [PROFUNDIDADE_MAX] * NUM_RAIOS
        raio_angulo = self.angulo - (FOV / 2)
        largura_coluna = LARGURA // NUM_RAIOS

        for raio in range(NUM_RAIOS):
            sin_a = math.sin(raio_angulo) or 0.0001
            cos_a = math.cos(raio_angulo) or 0.0001

            distancia = 0
            atingiu = False
            tipo_bloco = 1
            hit_x, hit_y = 0.0, 0.0

            while not atingiu and distancia < PROFUNDIDADE_MAX:
                distancia += 0.04
                hit_x = self.px + cos_a * distancia
                hit_y = self.py + sin_a * distancia
                tx, ty = int(hit_x), int(hit_y)

                if tx < 0 or tx >= 8 or ty < 0 or ty >= 8:
                    atingiu = True
                    distancia = PROFUNDIDADE_MAX
                elif MAPA_QUARTO[ty][tx] > 0:
                    atingiu = True
                    tipo_bloco = MAPA_QUARTO[ty][tx]

            dist_corrigida = distancia * math.cos(self.angulo - raio_angulo)
            z_buffer[raio] = dist_corrigida
            altura_parede = min(ALTURA, int(ALTURA / (dist_corrigida + 0.0001)))

            sombra = self.calcular_fator_luz(raio_angulo, dist_corrigida)

            pos_x = raio * largura_coluna
            pos_y = (ALTURA // 2) - (altura_parede // 2)

            if tipo_bloco == 1:
                cor_parede = (int(125 * sombra), int(128 * sombra), int(138 * sombra))
                self.pg.draw.rect(self.tela, cor_parede, (pos_x, pos_y, largura_coluna + 1, altura_parede))
                alt_rodape = max(2, int(altura_parede * 0.08))
                self.pg.draw.rect(self.tela, (int(70 * sombra), int(70 * sombra), int(78 * sombra)),
                                  (pos_x, pos_y + altura_parede - alt_rodape, largura_coluna + 1, alt_rodape))

            elif tipo_bloco == 2:
                u = hit_y % 1.0
                cor_parede = (int(125 * sombra), int(128 * sombra), int(138 * sombra))
                self.pg.draw.rect(self.tela, cor_parede, (pos_x, pos_y, largura_coluna + 1, altura_parede))

                if 0.15 <= u <= 0.85:
                    alt_porta = int(altura_parede * 0.86)
                    topo_porta = pos_y + (altura_parede - alt_porta)

                    if u < 0.19 or u > 0.81:
                        cor_porta = (int(60 * sombra), int(35 * sombra), int(20 * sombra))
                    else:
                        tom_tabua = 1.0 if int(u * 18) % 2 == 0 else 0.88
                        cor_porta = (
                            int(140 * sombra * tom_tabua),
                            int(84 * sombra * tom_tabua),
                            int(46 * sombra * tom_tabua)
                        )

                    self.pg.draw.rect(self.tela, cor_porta, (pos_x, topo_porta, largura_coluna + 1, alt_porta))

                    if 0.48 <= u <= 0.52:
                        y_olho = topo_porta + int(alt_porta * 0.32)
                        raio_olho = max(2, int(altura_parede * 0.015))
                        self.pg.draw.circle(self.tela, (int(210 * sombra), int(210 * sombra), int(220 * sombra)),
                                            (pos_x + largura_coluna // 2, y_olho), raio_olho)
                        self.pg.draw.circle(self.tela, (10, 10, 15),
                                            (pos_x + largura_coluna // 2, y_olho), max(1, raio_olho // 2))

                    if 0.72 <= u <= 0.76:
                        y_macaneta = topo_porta + int(alt_porta * 0.54)
                        raio_mac = max(2, int(altura_parede * 0.02))
                        self.pg.draw.circle(self.tela, (int(240 * sombra), int(200 * sombra), int(65 * sombra)),
                                            (pos_x + largura_coluna // 2, y_macaneta), raio_mac)

            elif tipo_bloco == 3:
                u = hit_x % 1.0
                cor_parede = (int(125 * sombra), int(128 * sombra), int(138 * sombra))
                self.pg.draw.rect(self.tela, cor_parede, (pos_x, pos_y, largura_coluna + 1, altura_parede))

                if 0.12 <= u <= 0.88:
                    topo_jan = pos_y + int(altura_parede * 0.18)
                    alt_jan = int(altura_parede * 0.52)

                    if u < 0.16 or u > 0.84 or (0.48 <= u <= 0.52 and not self.janela_aberta):
                        cor_mold = (int(95 * sombra), int(58 * sombra), int(34 * sombra))
                        self.pg.draw.rect(self.tela, cor_mold, (pos_x, topo_jan, largura_coluna + 1, alt_jan))
                    else:
                        cor_ceu = (14, 22, 42) if self.janela_aberta else (int(35 * sombra + 15), int(55 * sombra + 25), int(95 * sombra + 45))
                        self.pg.draw.rect(self.tela, cor_ceu, (pos_x, topo_jan, largura_coluna + 1, alt_jan))

                        if self.hater_na_janela and 0.30 <= u <= 0.70:
                            y_cabeca = topo_jan + int(alt_jan * 0.45)
                            alt_hater = int(alt_jan * 0.65)
                            self.pg.draw.rect(self.tela, (25, 25, 30), (pos_x, y_cabeca, largura_coluna + 1, alt_hater))
                            if (0.38 <= u <= 0.43) or (0.57 <= u <= 0.62):
                                self.pg.draw.rect(self.tela, (255, 230, 80), (pos_x, y_cabeca + int(alt_hater * 0.22), largura_coluna + 1, max(2, int(alt_jan * 0.06))))

            raio_angulo += DELTA_ANGULO

        sprite_pc_atual = self.sprite_mesa_pc_ligado if self.pc_ligado else self.sprite_mesa_pc_desligado
        objetos_3d = [
            (self.mesa_pos[0], self.mesa_pos[1], sprite_pc_atual, 1.15, "MOVEL"),
            (self.cadeira_pos[0], self.cadeira_pos[1], self.sprite_cadeira, 0.85, "MOVEL"),
            (self.cama_pos[0], self.cama_pos[1], self.sprite_cama, 1.10, "MOVEL"),
            (self.armario_pos[0], self.armario_pos[1], self.sprite_armario, 0.80, "MOVEL"),
        ]

        if self.fantasma_ativo:
            flutuacao = math.sin(time.time() * 4.0) * 0.05
            objetos_3d.append((self.fantasma_pos[0], self.fantasma_pos[1], self.sprite_fantasma, 1.15 + flutuacao, "FANTASMA"))

        objetos_3d.sort(key=lambda obj: math.hypot(obj[0] - self.px, obj[1] - self.py), reverse=True)

        for ox, oy, sprite, escala, tipo_obj in objetos_3d:
            self.desenhar_sprite_3d(ox, oy, sprite, escala, z_buffer, tipo_obj)

        self.desenhar_lanterna_mao()

    def desenhar_sprite_3d(self, ox, oy, sprite, escala, z_buffer, tipo_obj):
        dx = ox - self.px
        dy = oy - self.py
        distancia = math.hypot(dx, dy)
        if distancia < 0.25:
            return

        angulo_mundo = math.atan2(dy, dx)
        angulo_obj = angulo_mundo - self.angulo
        while angulo_obj > math.pi:
            angulo_obj -= 2 * math.pi
        while angulo_obj < -math.pi:
            angulo_obj += 2 * math.pi

        if abs(angulo_obj) < (FOV / 2) + 0.45:
            dist_perp = distancia * math.cos(angulo_obj)
            if dist_perp <= 0.2:
                return

            tamanho_proj = int((ALTURA / dist_perp) * escala)
            centro_x = int((0.5 + (angulo_obj / FOV)) * LARGURA)
            topo_y = (ALTURA // 2) + int((ALTURA / dist_perp) * 0.5) - tamanho_proj

            sprite_redim = self.pg.transform.scale(sprite, (tamanho_proj, tamanho_proj)).copy()

            luz = self.calcular_fator_luz(angulo_mundo, dist_perp)
            if tipo_obj == "FANTASMA":
                progresso_sumir = min(1.0, self.luz_no_fantasma / 1.8)
                opacidade = int(255 * (1.0 - progresso_sumir) * max(0.25, luz))
                sprite_redim.set_alpha(opacidade)
            else:
                escurecer = int(255 * luz)
                sprite_redim.fill((escurecer, escurecer, escurecer), special_flags=self.pg.BLEND_RGBA_MULT)

            largura_coluna = LARGURA // NUM_RAIOS
            for col_px in range(tamanho_proj):
                tela_x = centro_x - (tamanho_proj // 2) + col_px
                if 0 <= tela_x < LARGURA:
                    raio_idx = min(NUM_RAIOS - 1, tela_x // largura_coluna)
                    if dist_perp < z_buffer[raio_idx]:
                        self.tela.blit(sprite_redim, (tela_x, topo_y), (col_px, 0, 1, tamanho_proj))

    def desenhar_lanterna_mao(self):
        lx, ly = LARGURA - 175, ALTURA - 120
        self.pg.draw.polygon(self.tela, (35, 38, 45), [(lx + 50, ly + 120), (lx + 115, ly + 120), (lx + 75, ly + 35), (lx + 35, ly + 45)])
        self.pg.draw.polygon(self.tela, (55, 60, 70), [(lx + 28, ly + 48), (lx + 82, ly + 32), (lx + 72, ly + 12), (lx + 22, ly + 26)])
        cor_lente = (255, 245, 170) if (self.lanterna_ligada and self.bateria > 0) else (40, 45, 50)
        self.pg.draw.ellipse(self.tela, cor_lente, (lx + 24, ly + 14, 48, 16))

    # ==========================================
    # TELAS DE INTERFACE (PC, QUARTO, OLHO MÁGICO, JANELA, DEBAIXO DA CAMA)
    # ==========================================

    def desenhar_menu_pc(self):
        self.tela.fill((12, 16, 24))
        self.pg.draw.rect(self.tela, (0, 200, 255), (180, 120, LARGURA - 360, ALTURA - 240), 2, border_radius=12)

        t1 = self.fonte_grande.render("COMPUTADOR DO STREAMER", True, (0, 220, 255))
        self.tela.blit(t1, (LARGURA // 2 - t1.get_width() // 2, 150))

        estado_pc_txt = "LIGADO" if self.pc_ligado else "DESLIGADO (Tela Preta)"
        cor_pc = (100, 255, 140) if self.pc_ligado else (255, 100, 100)
        st_render = self.fonte_hud.render(f"Estado atual: {estado_pc_txt}", True, cor_pc)
        self.tela.blit(st_render, (LARGURA // 2 - st_render.get_width() // 2, 205))

        if self.pc_ligado:
            op1 = self.fonte_hud.render("[1] Entrar na Transmissão / Live", True, (240, 240, 240))
            op2 = self.fonte_hud.render("[2] Desligar o PC (Desligue a lanterna [F] também!)", True, (255, 220, 110))
            op3 = self.fonte_pequena.render("[ESC] Voltar ao quarto", True, (160, 160, 160))
            self.tela.blit(op1, (205, 275))
            self.tela.blit(op2, (205, 320))
            self.tela.blit(op3, (205, 390))
        else:
            op1 = self.fonte_hud.render("[1] Ligar o PC de volta", True, (100, 255, 140))
            op2 = self.fonte_pequena.render("[ESC] Voltar ao quarto (deixar PC desligado)", True, (160, 160, 160))
            self.tela.blit(op1, (230, 285))
            self.tela.blit(op2, (230, 345))

    def desenhar_tela_pc(self):
        self.tela.fill((15, 20, 30))
        self.pg.draw.rect(self.tela, (40, 45, 60), (20, 18, LARGURA - 40, ALTURA - 36), border_radius=12)
        self.pg.draw.rect(self.tela, (12, 14, 22), (35, 32, LARGURA - 70, ALTURA - 64))

        self.pg.draw.rect(self.tela, (25, 30, 45), (35, 32, LARGURA - 70, 45))
        status = "🔴 AO VIVO" if self.em_live else "⚪ OFFLINE"
        cor_st = (255, 60, 60) if self.em_live else (180, 180, 180)
        hora_atual = self.obter_horario_formatado()
        self.tela.blit(self.fonte_hud.render(f"{status} | 🕒 {hora_atual}", True, cor_st), (50, 45))

        metricas = f"👍 {self.likes_live} | 👎 {self.dislikes_live} | ➕ {self.inscritos_live} subs"
        self.tela.blit(self.fonte_hud.render(metricas, True, (255, 255, 255)), (530, 45))

        cam_x, cam_y, cam_w, cam_h = 50, 95, 450, 255
        self.pg.draw.rect(self.tela, (20, 25, 38), (cam_x, cam_y, cam_w, cam_h))
        self.pg.draw.rect(self.tela, (0, 200, 255), (cam_x, cam_y, cam_w, cam_h), 2)
        self.tela.blit(self.fonte_chat.render("[● REC] WEBCAM HD 1080p", True, (255, 70, 70)), (cam_x + 12, cam_y + 10))

        self.pg.draw.circle(self.tela, (230, 190, 150), (cam_x + 90, cam_y + 125), 30)
        self.pg.draw.circle(self.tela, (20, 20, 20), (cam_x + 80, cam_y + 120), 4)
        self.pg.draw.circle(self.tela, (20, 20, 20), (cam_x + 100, cam_y + 120), 4)
        self.pg.draw.arc(self.tela, (20, 20, 20), (cam_x + 80, cam_y + 126, 20, 12), math.pi, 2 * math.pi, 2)
        self.pg.draw.rect(self.tela, (50, 130, 220), (cam_x + 58, cam_y + 160, 64, 75), border_radius=8)

        self.pg.draw.rect(self.tela, (245, 245, 245), (cam_x + 145, cam_y + 75, 285, 90), border_radius=10)
        self.tela.blit(self.fonte_pequena.render(f"\"{self.fala_personagem[:26]}", True, (15, 15, 15)), (cam_x + 155, cam_y + 92))
        if len(self.fala_personagem) > 26:
            self.tela.blit(self.fonte_pequena.render(f"{self.fala_personagem[26:52]}\"", True, (15, 15, 15)), (cam_x + 155, cam_y + 118))

        chat_x, chat_y, chat_w, chat_h = 515, 95, 335, 465
        self.pg.draw.rect(self.tela, (18, 22, 32), (chat_x, chat_y, chat_w, chat_h))
        self.pg.draw.rect(self.tela, (70, 80, 100), (chat_x, chat_y, chat_w, chat_h), 2)
        self.tela.blit(self.fonte_hud.render("CHAT DA LIVE", True, (0, 220, 255)), (chat_x + 12, chat_y + 10))
        self.pg.draw.line(self.tela, (60, 70, 85), (chat_x + 10, chat_y + 36), (chat_x + chat_w - 10, chat_y + 36), 1)

        y_msg = chat_y + 46
        for autor, msg, cor_nick in self.historico_chat:
            linha_completa = f"{autor}: {msg}"
            p1 = linha_completa[:36]
            p2 = linha_completa[36:72]
            self.tela.blit(self.fonte_chat.render(p1, True, cor_nick), (chat_x + 12, y_msg))
            y_msg += 18
            if p2:
                self.tela.blit(self.fonte_chat.render(p2, True, cor_nick), (chat_x + 12, y_msg))
                y_msg += 18
            y_msg += 4

        if self.digitando_fala:
            self.pg.draw.rect(self.tela, (30, 40, 60), (50, 370, 450, 190), border_radius=8)
            self.pg.draw.rect(self.tela, (0, 255, 255), (50, 370, 450, 190), 2, border_radius=8)
            self.tela.blit(self.fonte_pequena.render("DIGITE SUA FALA (ENTER para enviar):", True, (0, 255, 255)), (65, 390))

            self.pg.draw.rect(self.tela, (10, 12, 18), (65, 425, 420, 42))
            cursor = "|" if int(time.time() * 2) % 2 == 0 else ""
            self.tela.blit(self.fonte_pequena.render(self.texto_digitado + cursor, True, (255, 255, 255)), (75, 437))
            self.tela.blit(self.fonte_chat.render("[ESC] Cancelar", True, (180, 180, 180)), (65, 485))
        else:
            opcoes = [
                "[1] Falar com o chat (Digitar)",
                "[2] Fazer jogada épica (Risco)",
                "[3] Ficar em silêncio",
                "[4] SAIR DO PC (Checar quarto/cama/janela)",
                "[5] Encerrar transmissão"
            ]
            y_op = 372
            for op in opcoes:
                cor_op = (255, 230, 110) if "[4]" in op else (225, 225, 225)
                self.tela.blit(self.fonte_hud.render(op, True, cor_op), (55, y_op))
                y_op += 36

    def desenhar_hud_quarto_3d(self):
        tam = 15
        ox = LARGURA - (8 * tam) - 15
        oy = 15
        self.pg.draw.rect(self.tela, (0, 0, 0), (ox - 3, oy - 3, 8 * tam + 6, 8 * tam + 6))
        for y in range(8):
            for x in range(8):
                b = MAPA_QUARTO[y][x]
                if b == 1:
                    cor = (90, 90, 90)
                elif b == 2:
                    cor = (160, 95, 50)
                elif b == 3:
                    cor = (80, 170, 230)
                else:
                    cor = (22, 22, 26)
                self.pg.draw.rect(self.tela, cor, (ox + x * tam, oy + y * tam, tam - 1, tam - 1))

        cor_pc_mini = (0, 200, 255) if self.pc_ligado else (60, 70, 80)
        self.pg.draw.rect(self.tela, cor_pc_mini, (ox + int(self.mesa_pos[0] * tam) - 6, oy + int(self.mesa_pos[1] * tam) - 3, 12, 6))
        self.pg.draw.circle(self.tela, (200, 60, 70), (ox + int(self.cadeira_pos[0] * tam), oy + int(self.cadeira_pos[1] * tam)), 3)
        self.pg.draw.rect(self.tela, (70, 100, 180), (ox + int(self.cama_pos[0] * tam) - 3, oy + int(self.cama_pos[1] * tam) - 6, 6, 12))
        self.pg.draw.rect(self.tela, (160, 110, 60), (ox + int(self.armario_pos[0] * tam) - 3, oy + int(self.armario_pos[1] * tam) - 3, 6, 6))

        jx = ox + int(self.px * tam)
        jy = oy + int(self.py * tam)
        self.pg.draw.circle(self.tela, (255, 255, 0), (jx, jy), 4)
        self.pg.draw.line(self.tela, (255, 255, 0), (jx, jy), (jx + int(math.cos(self.angulo) * 10), jy + int(math.sin(self.angulo) * 10)), 2)

        hora_atual = self.obter_horario_formatado()
        self.tela.blit(self.fonte_aviso.render(f"🕒 {hora_atual} / 06:00 AM", True, (255, 255, 255)), (15, 12))

        if not self.pc_ligado:
            st = "⚫ PC DESLIGADO (Apague a lanterna [F] também!)" if self.lanterna_ligada else "⚫ TUDO DESLIGADO (Silêncio total...)"
            cor_st = (255, 200, 100) if self.lanterna_ligada else (130, 255, 150)
        elif self.em_live:
            st = "🔴 LIVE ATIVA (Você saiu da cadeira)"
            cor_st = (255, 90, 90)
        else:
            st = "⚪ LIVE OFFLINE"
            cor_st = (210, 210, 210)

        self.tela.blit(self.fonte_pequena.render(st, True, cor_st), (15, 42))

        estado_lant = "LIGADA [F]" if (self.lanterna_ligada and self.bateria > 0) else "DESLIGADA [F]"
        self.tela.blit(self.fonte_chat.render(f"Lanterna: {estado_lant}", True, (240, 230, 140)), (15, 66))
        self.pg.draw.rect(self.tela, (50, 50, 55), (15, 86, 140, 14), border_radius=3)
        cor_bat = (80, 230, 100) if self.bateria > 40 else (240, 180, 40) if self.bateria > 15 else (230, 50, 50)
        self.pg.draw.rect(self.tela, cor_bat, (17, 88, int(136 * (self.bateria / 100.0)), 10), border_radius=2)

        self.tela.blit(self.fonte_chat.render("WASD: Andar | Setas: Girar | F: Lanterna | E: Interagir", True, (160, 160, 160)), (15, 108))

        if self.mae_no_quarto:
            alerta_mae = self.fonte_aviso.render("⚠️ SUA MÃE ENTROU NO QUARTO! CORRA PARA A CAMA [E]!", True, (255, 90, 90))
            self.tela.blit(alerta_mae, (LARGURA // 2 - alerta_mae.get_width() // 2, 140))

        if self.aviso_status_timer > 0:
            txt_p = self.fonte_hud.render(self.texto_aviso_status, True, (100, 255, 140))
            self.tela.blit(txt_p, (LARGURA // 2 - txt_p.get_width() // 2, ALTURA - 95))

        alvo = self.verificar_interacao_proxima()
        if alvo == "PC":
            t = self.fonte_aviso.render("[E] Usar Computador (Transmitir / Desligar)", True, (0, 230, 255))
            self.tela.blit(t, (LARGURA // 2 - t.get_width() // 2, ALTURA - 55))
        elif alvo == "CAMA":
            t = self.fonte_aviso.render("[E] Esconder-se Debaixo da Cama", True, (150, 200, 255))
            self.tela.blit(t, (LARGURA // 2 - t.get_width() // 2, ALTURA - 55))
        elif alvo == "PORTA":
            t = self.fonte_aviso.render("[E] Olhar pelo Olho Mágico da Porta", True, (230, 190, 130))
            self.tela.blit(t, (LARGURA // 2 - t.get_width() // 2, ALTURA - 55))
        elif alvo == "JANELA":
            t = self.fonte_aviso.render("[E] Abrir Janela", True, (130, 210, 255))
            self.tela.blit(t, (LARGURA // 2 - t.get_width() // 2, ALTURA - 55))
        elif alvo == "ARMARIO":
            t = self.fonte_aviso.render("[E] Abrir Gaveta do Armário (Pegar Pilha)", True, (255, 220, 120))
            self.tela.blit(t, (LARGURA // 2 - t.get_width() // 2, ALTURA - 55))

    def desenhar_debaixo_da_cama(self):
        self.tela.fill((8, 8, 12))
        self.pg.draw.rect(self.tela, (28, 22, 18), (0, ALTURA // 2 + 40, LARGURA, ALTURA // 2))

        if self.mae_no_quarto:
            passo_x = int(math.sin(self.tempo_debaixo_cama * 3.5) * 180)
            mx = (LARGURA // 2) + passo_x
            my = ALTURA // 2 + 55

            self.pg.draw.rect(self.tela, (75, 45, 85), (mx - 45, my - 140, 32, 145))
            self.pg.draw.rect(self.tela, (75, 45, 85), (mx + 13, my - 140, 32, 145))
            self.pg.draw.ellipse(self.tela, (210, 120, 140), (mx - 50, my - 5, 42, 18))
            self.pg.draw.ellipse(self.tela, (210, 120, 140), (mx + 8, my - 5, 42, 18))

        self.pg.draw.rect(self.tela, (35, 20, 12), (0, 0, LARGURA, 115))
        self.pg.draw.rect(self.tela, (25, 14, 8), (0, 0, 55, ALTURA))
        self.pg.draw.rect(self.tela, (25, 14, 8), (LARGURA - 55, 0, 55, ALTURA))

        if self.lanterna_ligada:
            aviso_luz = self.fonte_aviso.render("APAGUE A LANTERNA [F] SENÃO ELA VAI TE VER!", True, (255, 80, 80))
            self.tela.blit(aviso_luz, (LARGURA // 2 - aviso_luz.get_width() // 2, 45))
        else:
            txt = self.fonte_pequena.render("Debaixo da cama... Fique quieto até ela sair ([E] para sair)", True, (150, 160, 180))
            self.tela.blit(txt, (LARGURA // 2 - txt.get_width() // 2, 45))

    def desenhar_tela_janela(self):
        self.tela.fill((12, 18, 34))

        self.pg.draw.circle(self.tela, (235, 235, 210), (LARGURA - 210, 135), 32)
        for sx, sy in [(220, 110), (310, 160), (480, 95), (610, 180), (260, 240)]:
            self.pg.draw.circle(self.tela, (200, 210, 240), (sx, sy), 2)

        self.pg.draw.rect(self.tela, (75, 45, 25), (0, 0, LARGURA, 45))
        self.pg.draw.rect(self.tela, (75, 45, 25), (0, ALTURA - 90, LARGURA, 90))
        self.pg.draw.rect(self.tela, (75, 45, 25), (0, 0, 70, ALTURA))
        self.pg.draw.rect(self.tela, (75, 45, 25), (LARGURA - 70, 0, 70, ALTURA))

        if self.hater_na_janela:
            offset_x = int(math.sin(self.animacao_soco * 25) * 28) if self.animacao_soco > 0 else 0
            offset_y = int(self.animacao_soco * 35) if self.animacao_soco > 0 else 0

            hx = (LARGURA // 2) + offset_x
            hy = (ALTURA // 2 + 30) + offset_y

            self.pg.draw.ellipse(self.tela, (22, 24, 30), (hx - 115, hy + 20, 230, 250))
            self.pg.draw.circle(self.tela, (28, 30, 38), (hx, hy - 40), 82)
            self.pg.draw.circle(self.tela, (215, 175, 145), (hx, hy - 35), 58)
            self.pg.draw.line(self.tela, (20, 20, 20), (hx - 35, hy - 55), (hx - 8, hy - 42), 6)
            self.pg.draw.line(self.tela, (20, 20, 20), (hx + 35, hy - 55), (hx + 8, hy - 42), 6)
            self.pg.draw.circle(self.tela, (20, 20, 20), (hx - 20, hy - 35), 6)
            self.pg.draw.circle(self.tela, (20, 20, 20), (hx + 20, hy - 35), 6)
            self.pg.draw.ellipse(self.tela, (120, 25, 25), (hx - 22, hy - 12, 44, 24))

            ax, ay = self.alvo_hater_pos
            pulso = int(math.sin(time.time() * 10) * 4)
            self.pg.draw.circle(self.tela, (255, 40, 40), (ax, ay), self.alvo_hater_raio + pulso)
            self.pg.draw.circle(self.tela, (255, 255, 255), (ax, ay), self.alvo_hater_raio + pulso, 3)
            self.pg.draw.circle(self.tela, (150, 0, 0), (ax, ay), 10)

            if self.animacao_soco > 0:
                self.pg.draw.circle(self.tela, (235, 195, 155), (ax, ay), 38)
                self.pg.draw.circle(self.tela, (255, 230, 90), (ax, ay), 48, 4)

            self.pg.draw.rect(self.tela, (40, 40, 45), (LARGURA // 2 - 150, 65, 300, 20), border_radius=4)
            self.pg.draw.rect(self.tela, (230, 60, 60), (LARGURA // 2 - 148, 67, int(296 * (self.vida_hater / 6.0)), 16), border_radius=3)

            instrucao = self.fonte_aviso.render("CLIQUE NOS CÍRCULOS VERMELHOS PARA SOCAR O HATER!", True, (255, 230, 90))
            self.tela.blit(instrucao, (LARGURA // 2 - instrucao.get_width() // 2, ALTURA - 58))
        else:
            txt = self.fonte_aviso.render("Ninguém na janela. Aperte [E] para fechar a janela.", True, (180, 210, 240))
            self.tela.blit(txt, (LARGURA // 2 - txt.get_width() // 2, ALTURA - 58))

    def desenhar_olho_magico(self):
        self.tela.fill((0, 0, 0))
        cx, cy = LARGURA // 2, ALTURA // 2
        raio_lente = 195

        lente = self.pg.Surface((raio_lente * 2, raio_lente * 2), self.pg.SRCALPHA)

        self.pg.draw.circle(lente, (18, 20, 28), (raio_lente, raio_lente), raio_lente)
        self.pg.draw.polygon(lente, (12, 13, 18), [(0, 0), (raio_lente - 55, raio_lente - 75), (raio_lente - 55, raio_lente + 95), (0, raio_lente * 2)])
        self.pg.draw.polygon(lente, (12, 13, 18), [(raio_lente * 2, 0), (raio_lente + 55, raio_lente - 75), (raio_lente + 55, raio_lente + 95), (raio_lente * 2, raio_lente * 2)])

        if self.ameaca_porta:
            progresso = min(1.0, self.tempo_encarando / self.tempo_necessario_encarar)
            escala = max(0.15, 1.0 - (progresso * 0.85))
            alpha = int(255 * max(0.0, 1.0 - (progresso ** 1.6)))

            passo_x = int(math.sin(self.tempo_encarando * 7.5) * 14 * escala)
            passo_y = int(abs(math.cos(self.tempo_encarando * 7.5)) * 7 * escala)

            pos_x = raio_lente + passo_x
            pos_y = int(raio_lente + 25 - (progresso * 45) + passo_y)

            largura_corpo = int(150 * escala)
            altura_corpo = int(250 * escala)
            raio_cabeca = max(4, int(44 * escala))

            camada_sombra = self.pg.Surface((raio_lente * 2, raio_lente * 2), self.pg.SRCALPHA)
            self.pg.draw.ellipse(camada_sombra, (3, 3, 5, alpha), (pos_x - largura_corpo // 2, pos_y - int(25 * escala), largura_corpo, altura_corpo))
            self.pg.draw.circle(camada_sombra, (3, 3, 5, alpha), (pos_x, pos_y - int(45 * escala)), raio_cabeca)

            raio_olho = max(1, int(7 * escala))
            dist_olhos = int(17 * escala)
            y_olhos = pos_y - int(48 * escala)
            brilho_vermelho = int(255 * max(0.0, 1.0 - (progresso * 1.15)))

            if brilho_vermelho > 10:
                self.pg.draw.circle(camada_sombra, (brilho_vermelho, 0, 0, alpha), (pos_x - dist_olhos, y_olhos), raio_olho)
                self.pg.draw.circle(camada_sombra, (brilho_vermelho, 0, 0, alpha), (pos_x + dist_olhos, y_olhos), raio_olho)

            lente.blit(camada_sombra, (0, 0))

        elif self.mae_na_porta:
            self.pg.draw.ellipse(lente, (85, 50, 95), (raio_lente - 75, raio_lente - 15, 150, 220))
            self.pg.draw.circle(lente, (215, 175, 145), (raio_lente, raio_lente - 50), 42)
            self.pg.draw.arc(lente, (60, 40, 30), (raio_lente - 44, raio_lente - 95, 88, 70), 0, math.pi, 14)
            self.pg.draw.line(lente, (30, 20, 15), (raio_lente - 24, raio_lente - 62), (raio_lente - 8, raio_lente - 55), 3)
            self.pg.draw.line(lente, (30, 20, 15), (raio_lente + 24, raio_lente - 62), (raio_lente + 8, raio_lente - 55), 3)
            self.pg.draw.circle(lente, (20, 20, 20), (raio_lente - 15, raio_lente - 50), 4)
            self.pg.draw.circle(lente, (20, 20, 20), (raio_lente + 15, raio_lente - 50), 4)

        mascara = self.pg.Surface((raio_lente * 2, raio_lente * 2), self.pg.SRCALPHA)
        self.pg.draw.circle(mascara, (255, 255, 255, 255), (raio_lente, raio_lente), raio_lente)
        lente.blit(mascara, (0, 0), special_flags=self.pg.BLEND_RGBA_MIN)

        self.tela.blit(lente, (cx - raio_lente, cy - raio_lente))
        self.pg.draw.circle(self.tela, (55, 58, 65), (cx, cy), raio_lente, 8)

    def desenhar_relatorio_final(self):
        self.tela.fill((12, 15, 24))
        self.pg.draw.rect(self.tela, (0, 200, 255), (150, 80, LARGURA - 300, ALTURA - 160), 3, border_radius=12)

        t1 = self.fonte_grande.render("TRANSMISSÃO ENCERRADA", True, (0, 220, 255))
        self.tela.blit(t1, (LARGURA // 2 - t1.get_width() // 2, 115))

        linhas = [
            f"Canal: {self.nome_canal}",
            f"Data e Hora: {self.dados_relatorio['data_hora']}",
            "----------------------------------------",
            f"➕ Inscritos ganhos : {self.dados_relatorio['inscritos']}",
            f"👍 Likes ganhos     : {self.dados_relatorio['likes']}",
            f"👎 Dislikes         : {self.dados_relatorio['dislikes']}",
            "----------------------------------------",
            f"Total acumulado: {self.total_inscritos} inscritos"
        ]
        y = 180
        for l in linhas:
            self.tela.blit(self.fonte_hud.render(l, True, (240, 240, 240)), (195, y))
            y += 34

        voltar = self.fonte_aviso.render("Aperte [ENTER] ou [E] para voltar ao quarto", True, (100, 255, 140))
        self.tela.blit(voltar, (LARGURA // 2 - voltar.get_width() // 2, ALTURA - 130))

    def desenhar_vitoria_6am(self):
        self.tela.fill((10, 25, 45))
        self.pg.draw.rect(self.tela, (255, 215, 80), (110, 55, LARGURA - 220, ALTURA - 110), 4, border_radius=14)

        t_hora = self.fonte_gigante.render("☀️ 06:00 AM ☀️", True, (255, 225, 90))
        t_sub = self.fonte_aviso.render("VOCÊ SOBREVIVEU À MADRUGADA DE STREAMING!", True, (130, 255, 160))
        self.tela.blit(t_hora, (LARGURA // 2 - t_hora.get_width() // 2, 85))
        self.tela.blit(t_sub, (LARGURA // 2 - t_sub.get_width() // 2, 145))

        pontos, subs, likes, dislikes = self.calcular_pontuacao_final()

        detalhes = [
            f"Streamer           : {self.nome_canal}",
            f"Inscritos totais   : {subs} (+{subs * 50} pts)",
            f"Likes totais       : {likes} (+{likes * 15} pts)",
            f"Ameaças evitadas   : {self.ameacas_sobrevividas} (+{self.ameacas_sobrevividas * 250} pts)",
            f"Dislikes recebidos : {dislikes} (-{dislikes * 20} pts)",
            "================================================",
            f"🏆 PONTUAÇÃO FINAL : {pontos} PONTOS"
        ]
        y = 205
        for idx, linha in enumerate(detalhes):
            cor_l = (255, 230, 90) if idx == len(detalhes) - 1 else (235, 235, 240)
            fonte_l = self.fonte_aviso if idx == len(detalhes) - 1 else self.fonte_hud
            self.tela.blit(fonte_l.render(linha, True, cor_l), (165, y))
            y += 38

        reiniciar = self.fonte_pequena.render("Aperte [R] para jogar outra noite ou [ESC] para sair", True, (180, 200, 220))
        self.tela.blit(reiniciar, (LARGURA // 2 - reiniciar.get_width() // 2, ALTURA - 95))

    def desenhar_gameover(self):
        if self.tipo_gameover == "MAE":
            self.tela.fill((45, 25, 60))
            self.pg.draw.circle(self.tela, (215, 175, 145), (LARGURA // 2, ALTURA // 2 - 40), 110)
            self.pg.draw.line(self.tela, (30, 20, 15), (LARGURA // 2 - 55, ALTURA // 2 - 70), (LARGURA // 2 - 15, ALTURA // 2 - 50), 6)
            self.pg.draw.line(self.tela, (30, 20, 15), (LARGURA // 2 + 55, ALTURA // 2 - 70), (LARGURA // 2 + 15, ALTURA // 2 - 50), 6)
            self.pg.draw.circle(self.tela, (20, 20, 20), (LARGURA // 2 - 35, ALTURA // 2 - 40), 10)
            self.pg.draw.circle(self.tela, (20, 20, 20), (LARGURA // 2 + 35, ALTURA // 2 - 40), 10)
            self.pg.draw.arc(self.tela, (150, 30, 30), (LARGURA // 2 - 40, ALTURA // 2 + 5, 80, 45), 0, math.pi, 5)
        elif self.tipo_gameover == "HATER":
            self.tela.fill((60, 20, 10))
            self.pg.draw.circle(self.tela, (25, 28, 35), (LARGURA // 2, ALTURA // 2 - 35), 120)
            self.pg.draw.circle(self.tela, (215, 175, 145), (LARGURA // 2, ALTURA // 2 - 30), 85)
            self.pg.draw.line(self.tela, (20, 20, 20), (LARGURA // 2 - 45, ALTURA // 2 - 60), (LARGURA // 2 - 10, ALTURA // 2 - 42), 7)
            self.pg.draw.line(self.tela, (20, 20, 20), (LARGURA // 2 + 45, ALTURA // 2 - 60), (LARGURA // 2 + 10, ALTURA // 2 - 42), 7)
            self.pg.draw.circle(self.tela, (20, 20, 20), (LARGURA // 2 - 28, ALTURA // 2 - 32), 9)
            self.pg.draw.circle(self.tela, (20, 20, 20), (LARGURA // 2 + 28, ALTURA // 2 - 32), 9)
        else:
            self.tela.fill((85, 0, 0))
            self.pg.draw.circle(self.tela, (0, 0, 0), (LARGURA // 2, ALTURA // 2 - 30), 135)
            self.pg.draw.circle(self.tela, (255, 255, 255), (LARGURA // 2 - 45, ALTURA // 2 - 60), 22)
            self.pg.draw.circle(self.tela, (255, 255, 255), (LARGURA // 2 + 45, ALTURA // 2 - 60), 22)
            self.pg.draw.circle(self.tela, (255, 0, 0), (LARGURA // 2 - 45, ALTURA // 2 - 60), 8)
            self.pg.draw.circle(self.tela, (255, 0, 0), (LARGURA // 2 + 45, ALTURA // 2 - 60), 8)
            self.pg.draw.ellipse(self.tela, (255, 255, 255), (LARGURA // 2 - 35, ALTURA // 2 + 10, 70, 65))

        t1 = self.fonte_grande.render(self.motivo_gameover, True, (255, 255, 255))
        t2 = self.fonte_hud.render("Aperte [R] para reiniciar ou [ESC] para sair", True, (220, 220, 220))
        self.tela.blit(t1, (LARGURA // 2 - t1.get_width() // 2, 55))
        self.tela.blit(t2, (LARGURA // 2 - t2.get_width() // 2, ALTURA - 60))

    # ==========================================
    # LOOP PRINCIPAL
    # ==========================================

    def executar(self):
        while True:
            dt = self.clock.tick(FPS) / 1000.0

            if self.aviso_status_timer > 0:
                self.aviso_status_timer = max(0.0, self.aviso_status_timer - dt)
            if self.animacao_soco > 0:
                self.animacao_soco = max(0.0, self.animacao_soco - dt)

            for evento in self.pg.event.get():
                if evento.type == self.pg.QUIT:
                    self.pg.quit()
                    sys.exit()

                # Clique nos CÍRCULOS VERMELHOS do Hater quando a janela está aberta
                if evento.type == self.pg.MOUSEBUTTONDOWN and evento.button == 1:
                    if self.estado == "JANELA" and self.hater_na_janela:
                        mx, my = evento.pos
                        ax, ay = self.alvo_hater_pos
                        if math.hypot(mx - ax, my - ay) <= self.alvo_hater_raio + 10:
                            self.vida_hater -= 1
                            self.animacao_soco = 0.25
                            if self.vida_hater <= 0:
                                self.hater_na_janela = False
                                self.janela_aberta = False
                                self.ameacas_sobrevividas += 1
                                self.likes_live += 20
                                self.inscritos_live += 10
                                self.mostrar_aviso_rapido("👊 Você acertou todos os golpes e espantou o Hater!", 3.0)
                                self.estado = "QUARTO_3D"
                            else:
                                self.gerar_novo_alvo_hater()

                if evento.type == self.pg.KEYDOWN:
                    # 1. Digitando fala dentro do PC
                    if self.estado == "NO_PC" and self.digitando_fala:
                        if evento.key == self.pg.K_RETURN:
                            self.processar_acao_live("FALAR", self.texto_digitado)
                            self.digitando_fala = False
                            self.texto_digitado = ""
                        elif evento.key == self.pg.K_ESCAPE:
                            self.digitando_fala = False
                            self.texto_digitado = ""
                        elif evento.key == self.pg.K_BACKSPACE:
                            self.texto_digitado = self.texto_digitado[:-1]
                        else:
                            if len(self.texto_digitado) < 50 and evento.unicode.isprintable():
                                self.texto_digitado += evento.unicode
                        continue

                    # 2. Menu de decisão do Computador
                    if self.estado == "MENU_PC":
                        if evento.key == self.pg.K_ESCAPE:
                            self.estado = "QUARTO_3D"
                        elif evento.key == self.pg.K_1:
                            if self.pc_ligado:
                                if not self.em_live:
                                    self.iniciar_nova_live()
                                self.estado = "NO_PC"
                            else:
                                self.pc_ligado = True
                                self.tempo_silencio_total = 0.0
                                self.mostrar_aviso_rapido("💻 Você ligou o PC de volta!", 2.0)
                                self.estado = "QUARTO_3D"
                        elif evento.key == self.pg.K_2 and self.pc_ligado:
                            self.pc_ligado = False
                            self.tempo_silencio_total = 0.0
                            self.mostrar_aviso_rapido("🔌 PC desligado! Apague a lanterna [F] também por 5s!", 3.0)
                            self.estado = "QUARTO_3D"
                        continue

                    if evento.key == self.pg.K_ESCAPE:
                        self.pg.quit()
                        sys.exit()

                    # 3. Ações dentro da Transmissão (PC Ligado)
                    if self.estado == "NO_PC":
                        if evento.key == self.pg.K_1:
                            self.digitando_fala = True
                            self.texto_digitado = ""
                        elif evento.key == self.pg.K_2:
                            self.processar_acao_live("JOGADA")
                        elif evento.key == self.pg.K_3:
                            self.processar_acao_live("SILENCIO")
                        elif evento.key == self.pg.K_4:
                            self.estado = "QUARTO_3D"
                            self.adicionar_mensagem_chat("AnaClara_BR", "ué onde ele foi? kkk", (180, 180, 255))
                        elif evento.key == self.pg.K_5:
                            self.encerrar_live()

                    # 4. Interações e Lanterna no Quarto 3D
                    elif self.estado == "QUARTO_3D":
                        if evento.key == self.pg.K_f:
                            if self.bateria > 0:
                                self.lanterna_ligada = not self.lanterna_ligada
                            else:
                                self.lanterna_ligada = False

                        elif evento.key == self.pg.K_e:
                            alvo = self.verificar_interacao_proxima()
                            if alvo == "PC":
                                self.estado = "MENU_PC"
                            elif alvo == "CAMA":
                                self.estado = "DEBAIXO_CAMA"
                                self.tempo_debaixo_cama = 0.0
                            elif alvo == "PORTA":
                                self.estado = "OLHO_MAGICO"
                                self.tempo_encarando = 0.0
                            elif alvo == "JANELA":
                                self.janela_aberta = True
                                self.estado = "JANELA"
                            elif alvo == "ARMARIO":
                                self.bateria = 100.0
                                self.lanterna_ligada = True
                                self.mostrar_aviso_rapido("🔋 Você abriu a gaveta e colocou uma pilha nova! (100%)", 2.5)

                    # 5. Debaixo da Cama (apagar lanterna com F ou sair com E)
                    elif self.estado == "DEBAIXO_CAMA":
                        if evento.key == self.pg.K_f:
                            if self.bateria > 0:
                                self.lanterna_ligada = not self.lanterna_ligada
                        elif evento.key == self.pg.K_e:
                            self.estado = "QUARTO_3D"
                            self.tempo_debaixo_cama = 0.0

                    # 6. Na Janela Aberta (fechar janela)
                    elif self.estado == "JANELA":
                        if evento.key == self.pg.K_e:
                            self.janela_aberta = False
                            self.estado = "QUARTO_3D"

                    # 7. Sair do Olho Mágico
                    elif self.estado == "OLHO_MAGICO":
                        if evento.key == self.pg.K_e:
                            self.estado = "QUARTO_3D"
                            self.tempo_encarando = 0.0

                    # 8. Sair do Relatório
                    elif self.estado == "RELATORIO":
                        if evento.key in (self.pg.K_RETURN, self.pg.K_e):
                            self.estado = "QUARTO_3D"

                    # 9. Reiniciar na Vitória ou Game Over
                    elif self.estado in ("GAME_OVER", "VITORIA"):
                        if evento.key == self.pg.K_r:
                            self.__init__(self.nome_canal)

            # Avança o relógio da noite (12 minutos = 720s até 06:00 AM)
            if self.estado in ("QUARTO_3D", "NO_PC", "MENU_PC", "OLHO_MAGICO", "JANELA", "DEBAIXO_CAMA", "RELATORIO"):
                self.tempo_sobrevivido += dt
                if self.tempo_sobrevivido >= DURACAO_NOITE_SEGUNDOS:
                    self.estado = "VITORIA"
                    continue

            # Bot de Chat IA
            if self.em_live and self.pc_ligado and self.estado in ("NO_PC", "QUARTO_3D"):
                self.timer_bot_chat += dt
                if self.timer_bot_chat >= 3.8:
                    self.timer_bot_chat = 0.0
                    self.gerar_mensagem_ia_chat("NORMAL")

            # Consumo de bateria da lanterna
            if self.estado in ("QUARTO_3D", "DEBAIXO_CAMA") and self.lanterna_ligada:
                self.bateria = max(0.0, self.bateria - (3.2 * dt))
                if self.bateria == 0.0:
                    self.lanterna_ligada = False

            # Lógica da Mãe Fase 1 (Na Porta): Precisa desligar o PC E a Lanterna por 5s!
            if self.mae_na_porta:
                if not self.pc_ligado and not self.lanterna_ligada:
                    self.tempo_silencio_total += dt
                    if self.tempo_silencio_total >= 5.0:
                        self.mae_na_porta = False
                        self.ameacas_sobrevividas += 1
                        self.mostrar_aviso_rapido("🤫 Sua mãe achou que você dormiu e foi embora! Ligue o PC.", 3.5)
                        self.adicionar_mensagem_chat("Sistema", "Sua mãe saiu da porta. Ligue o PC de volta!", (120, 255, 150))
                else:
                    self.tempo_silencio_total = 0.0

                if self.mae_na_porta and time.time() > self.tempo_limite_mae_porta:
                    self.mae_na_porta = False
                    self.mae_no_quarto = True
                    self.tempo_limite_esconder = time.time() + 7.5
                    self.mostrar_aviso_rapido("🚪 *TOC TOC!* SUA MÃE ENTROU! ESCONDA-SE DEBAIXO DA CAMA [E]!", 4.0)

            # Lógica da Mãe Fase 2 (Dentro do Quarto): Ficar debaixo da cama por 5s
            if self.mae_no_quarto:
                if self.estado == "DEBAIXO_CAMA" and not self.lanterna_ligada:
                    self.tempo_debaixo_cama += dt
                    if self.tempo_debaixo_cama >= 5.0:
                        self.mae_no_quarto = False
                        self.tempo_debaixo_cama = 0.0
                        self.ameacas_sobrevividas += 1
                        self.estado = "QUARTO_3D"
                        self.mostrar_aviso_rapido("😮‍💨 Ela não te viu debaixo da cama e saiu do quarto!", 3.5)
                elif time.time() > self.tempo_limite_esconder:
                    self.motivo_gameover = "SUA MÃE TE PEGOU ACORDADO NO QUARTO!"
                    self.tipo_gameover = "MAE"
                    self.estado = "GAME_OVER"

            # Checa tempo limite das outras 3 ameaças
            if self.estado in ("QUARTO_3D", "NO_PC", "MENU_PC", "OLHO_MAGICO", "JANELA", "DEBAIXO_CAMA"):
                if self.ameaca_porta and time.time() > self.tempo_limite_porta:
                    self.motivo_gameover = "A SOMBRA ENTROU PELA PORTA..."
                    self.tipo_gameover = "MONSTRO"
                    self.estado = "GAME_OVER"
                elif self.fantasma_ativo and time.time() > self.tempo_limite_fantasma:
                    self.motivo_gameover = "VOCÊ FICOU NO PC E O FANTASMA TE PEGOU..."
                    self.tipo_gameover = "MONSTRO"
                    self.estado = "GAME_OVER"
                elif self.hater_na_janela and time.time() > self.tempo_limite_hater:
                    self.motivo_gameover = "O HATER PULOU A JANELA E QUEBROU SEU SETUP!"
                    self.tipo_gameover = "HATER"
                    self.estado = "GAME_OVER"

            # Atualização e Renderização
            if self.estado == "QUARTO_3D":
                self.mover_jogador(dt)

                if self.fantasma_ativo and self.lanterna_ligada and self.bateria > 0:
                    dx = self.fantasma_pos[0] - self.px
                    dy = self.fantasma_pos[1] - self.py
                    dist_f = math.hypot(dx, dy)
                    ang_f = math.atan2(dy, dx) - self.angulo
                    while ang_f > math.pi:
                        ang_f -= 2 * math.pi
                    while ang_f < -math.pi:
                        ang_f += 2 * math.pi

                    if abs(ang_f) < 0.35 and dist_f < 7.0:
                        self.luz_no_fantasma += dt
                        if self.luz_no_fantasma >= 1.8:
                            self.fantasma_ativo = False
                            self.luz_no_fantasma = 0.0
                            self.ameacas_sobrevividas += 1
                            self.likes_live += 25
                            self.inscritos_live += 12
                            self.mostrar_aviso_rapido("👻 Você espantou o fantasma com a lanterna!", 2.5)

                self.renderizar_3d()
                self.desenhar_hud_quarto_3d()

            elif self.estado == "MENU_PC":
                self.desenhar_menu_pc()

            elif self.estado == "NO_PC":
                self.desenhar_tela_pc()

            elif self.estado == "DEBAIXO_CAMA":
                self.desenhar_debaixo_da_cama()

            elif self.estado == "JANELA":
                self.desenhar_tela_janela()

            elif self.estado == "OLHO_MAGICO":
                if self.ameaca_porta:
                    self.tempo_encarando += dt
                    if self.tempo_encarando >= self.tempo_necessario_encarar:
                        self.ameaca_porta = False
                        self.tempo_encarando = 0.0
                        self.ameacas_sobrevividas += 1
                        self.likes_live += 20
                        self.inscritos_live += 10
                        self.adicionar_mensagem_chat("Lucas_Gameplay", "mano vc ouviu esse barulho aí??", (130, 255, 160))
                self.desenhar_olho_magico()

            elif self.estado == "RELATORIO":
                self.desenhar_relatorio_final()

            elif self.estado == "VITORIA":
                self.desenhar_vitoria_6am()

            elif self.estado == "GAME_OVER":
                self.desenhar_gameover()

            self.pg.display.flip()


if __name__ == "__main__":
    if len(sys.argv) >= 3 and sys.argv[1] == "--jogar":
        jogo = JogoStreaming3D(sys.argv[2])
        jogo.executar()
    else:
        print("Acesse no navegador: http://127.0.0.1:5000")
        app.run(debug=True)