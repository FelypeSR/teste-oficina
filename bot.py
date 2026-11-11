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
    python bot.py

Comandos no chat:
    /temperatura 0.2   troca a temperatura no meio da conversa
    /temperatura       mostra a temperatura atual
    /limpar            apaga o histórico (começa uma conversa nova)
    /sair              encerra
"""

from datetime import date
from pathlib import Path

# =============================================================================
# 1. CONFIGURAÇÃO
# =============================================================================

# Nome da empresa atendida. Entra no lugar de {{NOME_EMPRESA}}.
NOME_EMPRESA = "Provedor Exemplo"

# Base de conhecimento (FAQ, planos, horários). Entra no lugar de {{CONTEXTO}}.
# Começa VAZIA de propósito: assim o bot deve responder que ainda não tem
# a informação e encaminhar para um atendente, como diz o SYSTEM_PROMPT.md.
CONTEXTO = ""

# TEMPERATURA: controla o quanto o modelo "arrisca" ao escolher as palavras.
#   - valores baixos (perto de 0): respostas mais previsíveis e repetitivas;
#   - valores altos: respostas mais variadas e criativas (e menos confiáveis).
# O intervalo aceito depende da API escolhida (muitas usam de 0 a 1 ou de 0 a 2).
# Também dá para trocar durante o chat com o comando /temperatura.
TEMPERATURA = 0.7

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
# 3. CHAMADA AO LLM  >>> PARTE DE VOCÊS <<<
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

    Passos típicos, seja qual for a API escolhida:
      1. Instalar o pacote (SDK) da API, ou fazer a requisição HTTP direto.
      2. Ler a chave de uma variável de ambiente. Nunca escrevam a chave
         no código nem façam commit dela.
      3. Enviar o system_prompt, as mensagens e a temperatura. Cada API
         tem o seu jeito de receber o prompt de sistema: algumas usam um
         campo separado, outras uma mensagem com role "system" no começo
         da lista.
      4. Pegar o texto da resposta e devolver com `return`.

    Atenção: nem todo modelo aceita o parâmetro de temperatura, e o
    intervalo de valores muda de uma API para outra. Confiram na
    documentação da API que escolherem.
    """
    raise NotImplementedError(
        "A função chamar_llm() ainda não foi implementada.\n"
        "Abra o bot.py, vá até a seção 3 e conecte a API do LLM que vocês escolheram."
    )


# =============================================================================
# 4. CHAT NO TERMINAL
# =============================================================================

def main() -> None:
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
