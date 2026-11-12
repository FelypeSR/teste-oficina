"""
bot.py — Suporte Bot, versão CRUA (oficina "Do Código à Produção").

O que este arquivo já faz:
  1. Lê o SYSTEM_PROMPT.md e troca as marcações {{NOME_EMPRESA}},
     {{CONTEXTO}} e {{DATA_ATUAL}} pelos valores reais.
  2. Abre um chat no terminal e guarda o histórico da conversa.
  3. Entrega o prompt, a conversa e a TEMPERATURA para a função
     chamar_llm() e mostra a resposta do modelo do jeito que ela vier.

O que fica para vocês:
  - Escolher a API do LLM e escrever a função chamar_llm() (seção 3).
  - Brincar com a temperatura e observar o que muda nas respostas.
  - Todo o resto que leva isso para produção (validar o JSON, tratar
    erros, testes, logs, etc.).

Como rodar:
    pip install -r requirements.txt   # instala groq e python-dotenv
    python bot.py

    A chave da API fica no arquivo .env (variável API_KEY), nunca no código.

Comandos no chat:
    /temperatura 0.2   troca a temperatura no meio da conversa
    /temperatura       mostra a temperatura atual
    /limpar            apaga o histórico (começa uma conversa nova)
    /sair              encerra
"""

import os
from datetime import date
from pathlib import Path

from dotenv import load_dotenv  # lê o arquivo .env e joga as variáveis em os.environ
from groq import Groq           # SDK oficial da Groq (API compatível com a da OpenAI)

# =============================================================================
# 1. CONFIGURAÇÃO
# =============================================================================

# Carrega o .env. Sem argumentos, o load_dotenv() procura o arquivo começando
# na pasta deste script e subindo pelas pastas-pai até achar um .env, então
# funciona tanto com o .env aqui dentro quanto com o da pasta de cima.
# Variáveis que já existem no ambiente (ex.: export API_KEY=...) NÃO são
# sobrescritas pelo .env.
load_dotenv()

# Chave da API da Groq, lida do .env (linha "API_KEY=..."). Nunca escreva a
# chave direto aqui: o .env fica fora do repositório (ou no .gitignore)
# justamente para ela não ir para o GitHub.
API_KEY = os.getenv("API_KEY")

# Modelo usado na Groq. A lista de modelos disponíveis (e quais estão sendo
# descontinuados) fica em https://console.groq.com/docs/models.
MODELO = "openai/gpt-oss-120b"

# Cliente da API, criado uma única vez e reaproveitado em todas as chamadas.
# Se a chave não foi encontrada, fica None e o main() avisa antes de começar.
cliente = Groq(api_key=API_KEY) if API_KEY else None

# Nome da empresa atendida. Entra no lugar de {{NOME_EMPRESA}}.
NOME_EMPRESA = "Provedor Exemplo"

# Base de conhecimento (FAQ, planos, horários). Entra no lugar de {{CONTEXTO}}.
# Começa VAZIA de propósito: assim o bot deve responder que ainda não tem
# a informação e encaminhar para um atendente, como diz o SYSTEM_PROMPT.md.
CONTEXTO = ""

# TEMPERATURA: controla o quanto o modelo "arrisca" ao escolher as palavras.
#   - valores baixos (perto de 0): respostas mais previsíveis e repetitivas;
#   - valores altos: respostas mais variadas e criativas (e menos confiáveis).
# Na Groq o intervalo aceito é de 0 a 2.
# Também dá para trocar durante o chat com o comando /temperatura.
TEMPERATURA = 0.3

# Arquivo com o prompt de sistema, na mesma pasta deste script.
ARQUIVO_PROMPT = Path(__file__).parent / "SYSTEM_PROMPT.md"


# =============================================================================
# 2. MONTAGEM DO PROMPT
# =============================================================================

def montar_system_prompt() -> str:
    """Lê o SYSTEM_PROMPT.md e devolve o prompt pronto para enviar ao modelo.

    Segue o passo a passo descrito no topo do próprio SYSTEM_PROMPT.md.
    """
    prompt = ARQUIVO_PROMPT.read_text(encoding="utf-8")

    # Remove o bloco <!-- ... --> de instruções do topo: ele é para humanos,
    # não para o modelo. Ficamos só com o que vem depois do "-->" que está
    # SOZINHO numa linha ("\n-->").
    # Cuidado: o exemplo de código dentro desse bloco também tem um "-->"
    # escrito (no split). Se cortássemos no primeiro "-->" do arquivo, como
    # o exemplo sugere, metade das instruções iria junto para o modelo.
    prompt = prompt.split("\n-->", 1)[1]

    # Data de hoje no formato brasileiro, ex.: 11/11/2026.
    hoje = date.today().strftime("%d/%m/%Y")

    # Troca as marcações pelos valores reais.
    prompt = (prompt.replace("{{NOME_EMPRESA}}", NOME_EMPRESA)
                    .replace("{{CONTEXTO}}", CONTEXTO)
                    .replace("{{DATA_ATUAL}}", hoje))
    return prompt.strip()


# =============================================================================
# 3. CHAMADA AO LLM (Groq)
# =============================================================================

def chamar_llm(system_prompt: str, mensagens: list[dict], temperatura: float) -> str:
    """Envia a conversa para o LLM e devolve o texto da resposta.

    Recebe:
      system_prompt → as regras do bot (o SYSTEM_PROMPT.md já montado).
      mensagens     → a conversa até agora, em ordem, no formato:
                          [{"role": "user",      "content": "pergunta 1"},
                           {"role": "assistant", "content": "resposta 1"},
                           {"role": "user",      "content": "pergunta 2"}]
                      A última mensagem é sempre a pergunta nova do cliente.
      temperatura   → o valor que vocês vão variar.

    Devolve:
      O texto que o modelo escreveu. Pelo SYSTEM_PROMPT.md, deveria ser um
      JSON com os campos resposta, fonte, encaminhar e categoria.

    Como funciona com a Groq:
      1. O pacote `groq` (SDK) já foi importado lá em cima.
      2. A chave vem do .env (API_KEY) e já está dentro do `cliente`.
      3. A Groq segue o formato da OpenAI: o prompt de sistema vai como a
         PRIMEIRA mensagem da lista, com role "system". Depois vem a
         conversa (user/assistant) do jeito que já está em `mensagens`.
      4. O texto da resposta fica em resposta.choices[0].message.content.
    """
    # Monta a lista final: regras do bot primeiro, depois o histórico.
    # Criamos uma lista NOVA para não colocar o "system" dentro do histórico
    # do main() (senão ele seria repetido a cada pergunta).
    mensagens_api = [{"role": "system", "content": system_prompt}] + mensagens

    # Chamada à API. Se a chave estiver errada, a internet cair ou o limite
    # de uso estourar, o SDK levanta uma exceção (groq.APIError e derivadas).
    # Tratar isso direito é uma das tarefas de "levar para produção".
    resposta = cliente.chat.completions.create(
        model=MODELO,             # qual modelo da Groq responder
        messages=mensagens_api,   # prompt de sistema + conversa inteira
        temperature=temperatura,  # 0 = previsível ... 2 = bem criativo
    )

    # A API pode devolver várias alternativas (choices); pedimos só uma,
    # então pegamos a primeira. `content` é o texto que o modelo escreveu.
    return resposta.choices[0].message.content


# =============================================================================
# 4. CHAT NO TERMINAL
# =============================================================================

def main() -> None:
    # Sem chave não tem como falar com a API: avisa e sai antes do chat.
    if cliente is None:
        print("API_KEY não encontrada.\n"
              "Crie um arquivo .env com a linha API_KEY=sua_chave_da_groq "
              "(nesta pasta ou numa pasta acima) e rode de novo.")
        return

    system_prompt = montar_system_prompt()
    temperatura = TEMPERATURA

    # Histórico da conversa. O LLM não tem memória entre uma chamada e
    # outra: a cada pergunta enviamos a conversa inteira de novo.
    mensagens: list[dict] = []

    print(f"Suporte Bot | {NOME_EMPRESA} | temperatura: {temperatura}")
    print("Comandos: /temperatura <valor>  /limpar  /sair\n")

    while True:
        try:
            entrada = input("Você: ").strip()
        except (EOFError, KeyboardInterrupt):  # Ctrl+D ou Ctrl+C
            print("\nAté logo!")
            break

        if not entrada:
            continue

        # ---- comandos ----
        if entrada == "/sair":
            print("Até logo!")
            break

        if entrada == "/limpar":
            mensagens = []
            print("(conversa apagada)\n")
            continue

        if entrada.startswith("/temperatura"):
            partes = entrada.split()
            if len(partes) == 2:
                try:
                    # Aceita "0.5" e também "0,5".
                    temperatura = float(partes[1].replace(",", "."))
                except ValueError:
                    print("(valor inválido, use um número, ex.: /temperatura 0.5)\n")
                    continue
            print(f"(temperatura: {temperatura})\n")
            continue

        # ---- pergunta para o LLM ----
        mensagens.append({"role": "user", "content": entrada})

        try:
            resposta = chamar_llm(system_prompt, mensagens, temperatura)
        except NotImplementedError as erro:
            print(f"\n{erro}")
            break

        # A resposta entra no histórico para o modelo "lembrar" da conversa.
        mensagens.append({"role": "assistant", "content": resposta})

        # Mostra a resposta CRUA, exatamente como o modelo devolveu.
        print(f"Bot: {resposta}\n")


if __name__ == "__main__":
    main()
