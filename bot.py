import discord
import asyncio
import os
import aiohttp
import random
from discord import app_commands
from discord.ext import commands
from datetime import datetime
import discord
import os
import aiohttp
from collections import Counter
import asyncio
from datetime import datetime, timedelta
from discord.ext import commands, tasks


bot = discord.Client(intents=discord.Intents.all())

bot = commands.Bot(command_prefix="!", intents=discord.Intents.all())

votacoes = {}
CARGO_AUTORIZADO_NOME = "bot eleições" 
CHAVE_SECRETA = "abogadoontop"


LOGS_DIR = "Logs"
if not os.path.exists(LOGS_DIR):
    os.makedirs(LOGS_DIR)


DOWNLOAD_FOLDER = 'downloads'
LOGATTACHMENT_FILE = 'attachments_log.txt'
DAYS_TO_DELETE = 20
AUTHORIZED_USER_ID = 1336022633715601491
GUILD_ID = 1182792368626335865
CHANNEL_ID = 1328901633551241342
ID_DO_DRAX = 1304961266405871762


enviando = False
canal_destino = None

async def enviar_linhas(channel: discord.TextChannel):
    global enviando
    enviando = True
    try:
        with open('conteudo.txt', 'r', encoding='utf-8') as arquivo:
            for linha in arquivo:
                if not enviando:
                    break
                # Substitui "@<username>" por uma menção real, se possível
                for member in channel.guild.members:
                    if f"@{member.name}" in linha or f"@{member.display_name}" in linha:
                        linha = linha.replace(f"@{member.name}", member.mention).replace(f"@{member.display_name}", member.mention)
                await channel.send(linha.strip())  # Envia para o canal selecionado
                await asyncio.sleep(1)
    except FileNotFoundError:
        print('Arquivo conteudo.txt não encontrado.')

@bot.tree.command(name='thatslife', description='Envia linhas de um arquivo para um canal')
async def comecar(interaction: discord.Interaction, channel: discord.TextChannel):
    global enviando
    if interaction.user.id != AUTHORIZED_USER_ID:
        await interaction.response.send_message('Você não tem permissão para usar este comando.', ephemeral=True)
        return
    await interaction.response.send_message(f'Enviando linhas para {channel.mention}...', ephemeral=True)
    await enviar_linhas(channel)

@bot.tree.command(name='bye', description='Para o envio de linhas')
async def parar(interaction: discord.Interaction):
    global enviando
    if interaction.user.id != AUTHORIZED_USER_ID:
        await interaction.response.send_message('Você não tem permissão para usar este comando.', ephemeral=True)
        return
    enviando = False
    await interaction.response.send_message('Envio de linhas parado.', ephemeral=True)






# Certifique-se de que a pasta de downloads existe
if not os.path.exists(DOWNLOAD_FOLDER):
    os.makedirs(DOWNLOAD_FOLDER)


@bot.event
async def on_ready():
    try:
        synced = await bot.tree.sync()
        print(f"Tudo certo {len(synced)} comandos sincronizados.")
    except Exception as e:
        print(f"Erro ao sincronizar comandos: {e}")
    print(f"{bot.user} está vivo.")





async def possui_cargo(usuario: discord.Member):
    return any(cargo.name == CARGO_AUTORIZADO_NOME for cargo in usuario.roles)


@bot.tree.command(name="votacao", description="Inicia uma votação")
async def votacao(
    interaction: discord.Interaction,
    titulo: str,
    opcao1: str,
    opcao2: str,
    tempo: int,  # Tempo em segundos
    opcao3: str = None,
    opcao4: str = None,
    voto_secreto: bool = True
):
    if not await possui_cargo(interaction.user):
        await interaction.response.send_message("Você não tem permissão para iniciar uma votação!", ephemeral=True)
        return

    votacao_id = interaction.id
    votacoes[votacao_id] = {
        "titulo": titulo,
        "opcoes": [op for op in [opcao1, opcao2, opcao3, opcao4] if op is not None],
        "votos": {opcao: [] for opcao in [opcao1, opcao2, opcao3, opcao4] if opcao is not None},
        "secreto": voto_secreto,
        "tempo": tempo,
        "canal": interaction.channel
    }

    embed = discord.Embed(title="📊 " + titulo, description="Dia de eleição!", color=discord.Color.blue())
    embed.add_field(name="ID da Votação", value=f"`{votacao_id}`", inline=False)
    for opcao in votacoes[votacao_id]["opcoes"]:
        embed.add_field(name="Candidato", value=opcao, inline=False)
    embed.set_footer(text=f"Voto secreto: {'Sim' if voto_secreto else 'Não'} | Tempo restante: {tempo} segundos")

    class VotacaoView(discord.ui.View):
        def __init__(self):
            super().__init__(timeout=None)
            for opcao in votacoes[votacao_id]["opcoes"]:
                self.add_item(VotacaoButton(opcao))

    class VotacaoButton(discord.ui.Button):
        def __init__(self, opcao):
            super().__init__(label=opcao, style=discord.ButtonStyle.primary)
            self.opcao = opcao

        async def callback(self, interaction: discord.Interaction):
            await registrar_voto(interaction, votacao_id, self.opcao)

    await interaction.response.send_message(embed=embed, view=VotacaoView())
    asyncio.create_task(contagem_regressiva(votacao_id))


async def contagem_regressiva(votacao_id: int):
    while votacoes[votacao_id]["tempo"] > 0:
        await asyncio.sleep(5)
        votacoes[votacao_id]["tempo"] -= 5

        if votacoes[votacao_id]["tempo"] <= 0:
            await enviar_resultado(votacao_id)
            return


async def registrar_voto(interaction: discord.Interaction, votacao_id: int, opcao: str):
    if votacao_id not in votacoes:
        await interaction.response.send_message("Esta votação já foi encerrada!", ephemeral=True)
        return

    for votos in votacoes[votacao_id]["votos"].values():
        if interaction.user.id in votos:
            await interaction.response.send_message("Você já votou!", ephemeral=True)
            return

    votacoes[votacao_id]["votos"][opcao].append(interaction.user.id)
    msg = "Seu voto foi registrado!" if votacoes[votacao_id]["secreto"] else f"Você votou em {opcao}!"
    await interaction.response.send_message(msg, ephemeral=True)


async def enviar_resultado(votacao_id: int):
    if votacao_id not in votacoes:
        return

    dados = votacoes[votacao_id]
    resultado_texto = "**Resultado da Votação:**\n\n"
    for opcao, votos in dados["votos"].items():
        if opcao:
            resultado_texto += f"**{opcao}** - {len(votos)} votos\n"

    embed = discord.Embed(title="Resultado da Votação", description=resultado_texto, color=discord.Color.dark_orange())
    embed.add_field(name="ID da Votação", value=f"`{votacao_id}`", inline=False)

    if not dados["secreto"]:
        lista_votos = "\n".join([f"**{opcao}**: " + ", ".join(f"<@{user_id}>" for user_id in votos) for opcao, votos in dados["votos"].items() if opcao])
        embed.add_field(name="Votantes:", value=lista_votos, inline=False)

    await dados["canal"].send(embed=embed)
    del votacoes[votacao_id]

historico_votacoes = {}  # Dicionário para armazenar votações encerradas

@bot.tree.command(name="ver_votantes", description="Veja todos os votantes de uma votação (mesmo que seja secreta ou encerrada)")
async def ver_votantes(interaction: discord.Interaction, votacao_id: str):
    if not await possui_cargo(interaction.user):
        await interaction.response.send_message("Você não tem permissão para ver os votantes!", ephemeral=True)
        return

    votacao_id = int(votacao_id)

    # Verifica se a votação está ativa ou no histórico
    dados = votacoes.get(votacao_id) or historico_votacoes.get(votacao_id)

    if not dados:
        await interaction.response.send_message("Votação não encontrada!", ephemeral=True)
        return

    lista_votos = "\n".join(
        [f"**{opcao}**: " + ", ".join(f"<@{user_id}>" for user_id in votos) for opcao, votos in dados["votos"].items()]
    )

    embed = discord.Embed(title=f"Votantes da Votação `{votacao_id}`", description=lista_votos or "Nenhum voto registrado.", color=discord.Color.gold())
    await interaction.response.send_message(embed=embed, ephemeral=True)


async def enviar_resultado(votacao_id: int):
    if votacao_id not in votacoes:
        return

    dados = votacoes[votacao_id]
    resultado_texto = "**Resultado da Votação:**\n\n"
    for opcao, votos in dados["votos"].items():
        if opcao:
            resultado_texto += f"**{opcao}** - {len(votos)} votos\n"

    embed = discord.Embed(title="Resultado da Votação", description=resultado_texto, color=discord.Color.dark_orange())
    embed.add_field(name="ID da Votação", value=f"`{votacao_id}`", inline=False)

    if not dados["secreto"]:
        lista_votos = "\n".join([f"**{opcao}**: " + ", ".join(f"<@{user_id}>" for user_id in votos) for opcao, votos in dados["votos"].items() if opcao])
        embed.add_field(name="Votantes:", value=lista_votos, inline=False)

    await dados["canal"].send(embed=embed)

    # Mover votação para o histórico
    historico_votacoes[votacao_id] = dados
    del votacoes[votacao_id]  # Remover da lista ativa



@bot.event
async def on_message(message):
    if message.author.bot:
        return  # Ignora mensagens de bots

    username = message.author.name
    user_id = message.author.id
    server_name = message.guild.name if message.guild else "DM"
    channel_name = message.channel.name if isinstance(message.channel, discord.TextChannel) else "DM"
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Criar pasta para o usuário se não existir
    user_folder = os.path.join(LOGS_DIR, f"{username}_{user_id}")
    if not os.path.exists(user_folder):
        os.makedirs(user_folder)

    # Nome do arquivo de log
    log_filename = os.path.join(user_folder, "mensagens.txt")

    log_entry = f"[{timestamp}] [{server_name}] [{channel_name}] {username} ({user_id}): {message.content}\n"

    # Salvar no arquivo
    with open(log_filename, "a", encoding="utf-8") as file:
        file.write(log_entry)

    await bot.process_commands(message)  # Garante que os comandos ainda funcionem



@bot.event
async def on_ready():
    print(f'Logado como {bot.user}')
    asyncio.create_task(clean_old_files())


@bot.event
async def on_message(message):
    if message.author == bot.user:
        return
    
    print(f'[{message.channel}] {message.author}: {message.content}')
    
    # Baixar anexos, se houver
    for attachment in message.attachments:
        await download_attachment(attachment)

async def download_attachment(attachment):
    filename = f"{DOWNLOAD_FOLDER}/{attachment.filename}"
    async with aiohttp.ClientSession() as session:
        async with session.get(attachment.url) as response:
            if response.status == 200:
                with open(filename, 'wb') as f:
                    f.write(await response.read())
                log_attachment(filename)

# Registra os arquivos baixados
def log_attachment(filename):
    with open(LOGATTACHMENT_FILE, 'a') as log:
        log.write(f"{filename} | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

# Exclui arquivos com mais de 20 dias
async def clean_old_files():
    while True:
        now = datetime.now()
        for file in os.listdir(DOWNLOAD_FOLDER):
            file_path = os.path.join(DOWNLOAD_FOLDER, file)
            if os.path.isfile(file_path):
                creation_time = datetime.fromtimestamp(os.path.getctime(file_path))
                if now - creation_time > timedelta(days=DAYS_TO_DELETE):
                    os.remove(file_path)
                    print(f'Arquivo excluído: {file}')
        await asyncio.sleep(86400)  # Executa a limpeza a cada 24 horas

@bot.tree.command(name="say", description="Envia uma mensagem para um canal específico")
async def say(interaction: discord.Interaction, channel: discord.TextChannel, message: str):
    if interaction.user.id != AUTHORIZED_USER_ID:
        await interaction.response.send_message("Você não tem permissão para usar este comando!", ephemeral=True)
        return
    
    try:
        await interaction.response.defer(thinking=False)
        await channel.send(message)
        await interaction.delete_original_response()
    except discord.Forbidden:
        print("Não foi possível deletar a mensagem do comando.")



@bot.tree.command(name="info", description="Mostra informações do servidor")
async def serverinfo(interaction: discord.Interaction):
    guild = interaction.guild

    if guild is None:
        await interaction.response.send_message("Este comando só pode ser usado em um servidor.", ephemeral=True)
        return

    # Membros ativos
    active_members = [member for member in guild.members if member.status != discord.Status.offline]

    # Banimentos
    bans = []
    async for ban_entry in guild.bans():
        bans.append(ban_entry)

    # Dono
    owner = guild.owner

    # Embed
    embed = discord.Embed(title=f"Informações do Servidor: {guild.name}", color=0x00FF00)
    embed.add_field(name="Dono", value=owner.name if owner else "Desconhecido", inline=False)   
    embed.add_field(name="Membros Ativos", value=len(active_members), inline=False)
    embed.add_field(name="Banimentos", value=len(bans), inline=False)
    embed.set_thumbnail(url=guild.icon.url if guild.icon else "")

    await interaction.response.send_message(embed=embed)

@bot.event
async def on_ready():
    print(f'Bot conectado como {bot.user}')
    try:
        synced = await bot.tree.sync()
        print(f'Slash commands sincronizados: {len(synced)} comandos')
    except Exception as e:
        print(f'Erro ao sincronizar comandos: {e}')

@bot.tree.command(name='deletar', description='Deleta uma mensagem pelo ID')
async def deletar(interaction: discord.Interaction, id_da_mensagem: str):
    if interaction.user.id != AUTHORIZED_USER_ID:
        await interaction.response.send_message('Você não tem permissão para usar este comando.', ephemeral=True)
        return

    try:
        mensagem = await interaction.channel.fetch_message(int(id_da_mensagem))
        await mensagem.delete()
        await interaction.response.send_message(f'Mensagem com ID {id_da_mensagem} deletada com sucesso!', ephemeral=True)
    except discord.NotFound:
        await interaction.response.send_message('Mensagem não encontrada.', ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f'Ocorreu um erro: {e}', ephemeral=True)



async def remover_timeout_amigo(member):
    """
    Remove o timeout de um usuário.

    Args:
        member (discord.Member): O objeto Member do usuário.
    """

    try:
        await member.edit(timed_out_until=None)  # Remove o timeout
        print(f"Timeout removido de {member.name} manualmente.")
    except discord.Forbidden:
        print(f"Não tenho permissão para remover o timeout de {member.name}.")
    except discord.HTTPException as e:
        print(f"Erro ao remover o timeout de {member.name}: {e}")

@bot.event
async def on_message(message):
    """
    Verifica se a mensagem privada contém a chave secreta e remove o timeout.
    """

    if isinstance(message.channel, discord.DMChannel) and message.content.startswith(CHAVE_SECRETA):
        try:
            usuario_id = int(message.content.split()[1])
            guild = bot.guilds[0]  # Assumindo que o bot está em apenas um servidor
            member = guild.get_member(usuario_id)
            if member:
                await remover_timeout_amigo(member)
                await message.channel.send("Timeout removido.")
            else:
                await message.channel.send("Usuário não encontrado.")
        except (ValueError, IndexError):
            await message.channel.send("Uso incorreto. Use `chave_secreta <id_do_usuario>`.")


bot.run(os.getenv("DISCORD_TOKEN"))
