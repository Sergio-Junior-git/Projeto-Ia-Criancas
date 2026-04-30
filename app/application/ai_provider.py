import json
import os
import random
import unicodedata
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from app.domain.catalog import DISCIPLINES, SCHOOL_LEVELS


DIFFICULTY_GUIDE = {
    1: "reconhecimento direto de palavra, simbolo ou ideia; uma etapa; alternativas bem distintas",
    2: "traducao curta, completar lacuna simples ou identificar informacao explicita",
    3: "aplicar a regra em uma frase curta, pequeno calculo ou interpretacao direta",
    4: "duas etapas de raciocinio, distratores parecidos e contexto um pouco maior",
    5: "interpretacao mais cuidadosa, comparacao entre ideias ou aplicacao em contexto novo, mas ainda com resposta objetiva",
}


class FallbackLearningAI:
    def __init__(self, primary, fallback):
        self.primary = primary
        self.fallback = fallback

    def generate_explanation(self, discipline, level, topic):
        try:
            return self.primary.generate_explanation(discipline, level, topic)
        except Exception as exc:
            print(f"[ai] Falha na explicacao por IA real. Usando gerador local: {exc}")
            return self.fallback.generate_explanation(discipline, level, topic)

    def generate_activity(self, discipline, level, topic, difficulty, excluded_questions=None):
        try:
            return self.primary.generate_activity(discipline, level, topic, difficulty, excluded_questions)
        except Exception as exc:
            print(f"[ai] Falha na questao por IA real. Usando gerador local: {exc}")
            return self.fallback.generate_activity(discipline, level, topic, difficulty, excluded_questions)

    def evaluate(self, expected_answer, user_answer, discipline, topic):
        return self.fallback.evaluate(expected_answer, user_answer, discipline, topic)


class GroqLearningAI:
    def __init__(self, api_key=None, model=None):
        self.api_key = api_key or os.getenv("GROQ_API_KEY", "").strip()
        self.model = model or os.getenv("GROQ_MODEL", "llama-3.1-8b-instant").strip()
        self.endpoint = "https://api.groq.com/openai/v1/chat/completions"
        if not self.api_key:
            raise ValueError("GROQ_API_KEY nao configurada.")

    def generate_explanation(self, discipline, level, topic):
        payload = self._chat(
            [
                {"role": "system", "content": "Voce e um professor brasileiro. Responda de forma curta, clara e adequada para criancas/adolescentes."},
                {"role": "user", "content": f"Explique o assunto '{topic}' de {DISCIPLINES[discipline]['name']} para o nivel {SCHOOL_LEVELS[level]}. Use 4 a 6 frases."},
            ],
            temperature=0.7,
        )
        return payload.strip()

    def generate_activity(self, discipline, level, topic, difficulty, excluded_questions=None):
        excluded = "\n".join(f"- {question}" for question in (excluded_questions or [])[-20:])
        difficulty_description = DIFFICULTY_GUIDE.get(difficulty, DIFFICULTY_GUIDE[1])
        prompt = f"""
Gere UMA questao nova para um estudante brasileiro.

Disciplina: {DISCIPLINES[discipline]['name']}
Nivel escolar: {SCHOOL_LEVELS[level]}
Assunto obrigatorio: {topic}
Dificuldade de 1 a 5: {difficulty}
Como interpretar a dificuldade: {difficulty_description}

Regras:
- A pergunta deve ser realmente sobre o assunto obrigatorio e ter UMA unica resposta objetiva.
- Nao repita nenhuma pergunta da lista de perguntas proibidas.
- Varie contexto, numeros, frase, personagens e tipo de raciocinio.
- A dificuldade deve aparecer no raciocinio: dificuldade 1 e reconhecimento; 2 e traducao/lacuna simples; 3 aplica regra; 4 tem duas etapas; 5 pede interpretacao ou comparacao objetiva.
- Retorne somente JSON valido, sem markdown.
- O JSON deve ter: type, question, expected_answer, hint e explanation.
- type deve ser "short_answer" ou "multiple_choice".
- Se type for "multiple_choice", inclua options com 4 alternativas e expected_answer igual a uma delas.
- Prefira multiple_choice sempre que o aluno puder responder de varios jeitos.
- Use short_answer somente para resposta de 1 a 4 palavras ou um numero.
- Nunca use perguntas abertas como "descreva", "explique com suas palavras", "conte sobre", "o que voce faz" ou "escreva uma rotina".
- Nunca gere uma expected_answer com frase longa. A resposta esperada deve ter no maximo 4 palavras.
- A dica deve ajudar sem entregar a resposta. Nao use dica generica como "releia o enunciado".
- A explanation deve explicar em uma frase por que a resposta esta correta.
- Use portugues simples e sem acentos se for palavra em lingua estrangeira.
- Nao faca perguntas pessoais nem use primeira/segunda pessoa no enunciado: evite "eu faço", "voce faz", "minha", "meu", "sua", "seu".
- Nao use estereotipos familiares, exemplo: "pai traz comida para casa".
- Prefira perguntas escolares objetivas: traducao, completar frase, interpretar texto curto ou identificar palavra.
- Para ingles ou espanhol, a resposta esperada deve ser em portugues brasileiro ou uma palavra simples do idioma estudado, conforme o enunciado pedir.
- Para o assunto familia em ingles, use palavras como mother/mae, father/pai, sister/irma, brother/irmao, grandmother/avo.
- Para o assunto rotina em ingles, use atividades objetivas como wake up/acordar, brush teeth/escovar os dentes, eat breakfast/tomar cafe, go to school/ir para a escola. Nao pergunte a rotina pessoal do aluno.
- Para rotina em ingles, prefira formulacoes como "Qual frase significa..." ou "Complete a frase..." em vez de perguntar o que alguem faz.
- Para rotina em ingles, nao use perguntas com "geralmente", "antes de ir para a escola", "preparar para a escola" ou horarios. Isso fica ambiguo.
- Para rotina em ingles, use somente estes formatos: traducao de frase curta, completar lacuna em frase curta ou identificar a acao em uma frase curta.

Exemplo valido:
{{"type":"multiple_choice","question":"Em ingles, qual frase significa 'eu acordo cedo'?","options":["I wake up early","I eat breakfast","I go to school","I brush my teeth"],"expected_answer":"I wake up early","hint":"Procure o verbo usado para acordar.","explanation":"'Wake up' significa acordar."}}

Perguntas proibidas:
{excluded or "- nenhuma ainda"}
"""
        last_error = None
        for _ in range(2):
            content = self._chat(
                [
                    {"role": "system", "content": "Voce cria atividades escolares objetivas e corrigiveis em JSON estrito. Nunca use markdown. Nunca faca perguntas abertas ou pessoais."},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.85,
            )
            try:
                activity = self._parse_activity(content)
                if activity["question"] in set(excluded_questions or []):
                    raise ValueError("A IA repetiu uma pergunta do historico.")
                self._validate_activity_quality(activity)
                return activity
            except ValueError as exc:
                last_error = exc
                excluded_questions = list(excluded_questions or []) + [content[:200]]
        raise last_error or ValueError("Nao foi possivel gerar questao valida pela IA.")

    def _chat(self, messages, temperature):
        body = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": 360,
            "response_format": {"type": "json_object"} if self._expects_json(messages) else None,
        }
        body = {key: value for key, value in body.items() if value is not None}
        request = Request(
            self.endpoint,
            data=json.dumps(body).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "http://localhost:5000",
                "X-Title": "Estudo no Hospital",
                "User-Agent": "EstudoNoHospital/1.0",
            },
            method="POST",
        )
        try:
            with urlopen(request, timeout=25) as response:
                data = json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="ignore")
            raise RuntimeError(f"Groq HTTP {exc.code}: {detail[:240]}") from exc
        except URLError as exc:
            raise RuntimeError(f"Groq indisponivel: {exc}") from exc

        choice = data.get("choices", [{}])[0]
        message = choice.get("message") or {}
        content = message.get("content")
        if isinstance(content, list):
            content = "".join(part.get("text", "") for part in content if isinstance(part, dict))
        if not content:
            finish_reason = choice.get("finish_reason", "desconhecido")
            print(f"[ai] Resposta Groq sem conteudo. finish_reason={finish_reason}; message={message}")
            raise ValueError("Groq respondeu sem conteudo utilizavel.")
        return content

    def _parse_activity(self, content):
        if not isinstance(content, str):
            raise ValueError("Resposta da IA nao veio como texto.")
        start = content.find("{")
        end = content.rfind("}")
        if start == -1 or end == -1:
            raise ValueError("Resposta da IA nao veio em JSON.")
        data = json.loads(content[start : end + 1])
        if "activity" in data and isinstance(data["activity"], dict):
            data = data["activity"]

        question = str(data.get("question") or data.get("pergunta") or "").strip()
        expected_answer = str(
            data.get("expected_answer")
            or data.get("answer")
            or data.get("correct_answer")
            or data.get("resposta")
            or data.get("resposta_correta")
            or ""
        ).strip()
        hint = str(data.get("hint") or data.get("dica") or "").strip()
        explanation = str(
            data.get("explanation")
            or data.get("feedback")
            or data.get("explicacao")
            or "Essa resposta combina com a regra pedida no enunciado."
        ).strip()
        options = [str(option).strip() for option in data.get("options") or data.get("alternatives") or data.get("alternativas") or [] if str(option).strip()]
        activity_type = data.get("type") or data.get("question_type") or ("multiple_choice" if options else "short_answer")

        if activity_type not in {"short_answer", "multiple_choice"} or not question or not expected_answer or not hint:
            raise ValueError("JSON da IA veio incompleto.")
        activity = {
            "type": activity_type,
            "question": question,
            "expected_answer": expected_answer,
            "hint": hint,
            "explanation": explanation,
        }
        if activity_type == "multiple_choice":
            if expected_answer not in options and len(options) >= 4:
                options[-1] = expected_answer
            if len(options) != 4 or expected_answer not in options:
                raise ValueError("Alternativas da IA vieram invalidas.")
            activity["options"] = options
        return activity

    def _validate_activity_quality(self, activity):
        text = self._clean(f"{activity['question']} {activity['expected_answer']} {activity['hint']}")
        blocked_fragments = [
            "meu pai",
            "minha mae",
            "sua familia",
            "traz comida",
            "bom homem",
            "boa mulher",
            "quem e seu",
            "qual e o nome do meu",
            "descreva",
            "explique com suas palavras",
            "conte sobre",
            "o que voce faz",
            "eu faco",
            "voce faz",
            "qual atividade eu",
            "qual atividade voce",
            "geralmente",
            "antes de ir para a escola",
            "preparar para a escola",
            "as 7h",
            "7h",
            "7 a.m",
            "sua rotina",
            "minha rotina",
            "escreva uma rotina",
            "todas as manhas antes de ir",
            "releia o enunciado",
            "pista principal",
        ]
        if any(fragment in text for fragment in blocked_fragments):
            raise ValueError("Questao da IA veio aberta, pessoal, generica ou com estereotipo.")

        answer_words = self._clean(activity["expected_answer"]).split()
        if activity["type"] == "short_answer" and len(answer_words) > 4:
            raise ValueError("Resposta curta da IA veio longa demais para correcao objetiva.")
        if activity["type"] == "multiple_choice":
            normalized_options = [self._clean(option) for option in activity.get("options", [])]
            if len(set(normalized_options)) != 4:
                raise ValueError("Alternativas da IA vieram repetidas ou equivalentes.")
            if self._clean(activity["expected_answer"]) not in normalized_options:
                raise ValueError("Resposta esperada nao aparece nas alternativas.")
        if len(activity["question"]) > 220:
            raise ValueError("Pergunta da IA veio longa demais.")
        if len(activity["hint"]) < 12:
            raise ValueError("Dica da IA veio curta demais.")

    def _clean(self, value):
        normalized = unicodedata.normalize("NFD", str(value).lower().strip())
        without_accents = "".join(char for char in normalized if unicodedata.category(char) != "Mn")
        return " ".join(without_accents.split())

    def _expects_json(self, messages):
        return any("JSON" in message.get("content", "") or "json" in message.get("content", "") for message in messages)


class LocalLearningAI:
    """Gerador local organizado por disciplina, serie e assunto."""

    def generate_explanation(self, discipline, level, topic):
        level_name = SCHOOL_LEVELS.get(level, "serie escolhida")
        discipline_name = DISCIPLINES.get(discipline, {}).get("name", "disciplina")
        starters = {
            "maternal": "Vamos aprender brincando, observando imagens, sons e palavras simples.",
            "infantil": "Nesta fase, o ideal e usar exemplos curtos, objetos do dia a dia e repeticao.",
            "fundamental_1": "Aqui vale resolver passo a passo e explicar o caminho com suas palavras.",
            "fundamental_2": "Agora o assunto pede mais atencao as regras, comparacoes e justificativas.",
            "medio": "Neste nivel, a ideia e interpretar o contexto, aplicar conceitos e defender a resposta.",
        }
        return (
            f"Em {discipline_name}, no nivel {level_name}, o assunto '{topic}' deve ser estudado com exemplos "
            f"adequados para essa etapa. {starters.get(level, starters['fundamental_1'])}"
        )

    def generate_activity(self, discipline, level, topic, difficulty, excluded_questions=None):
        handlers = {
            "matematica": self._math_activity,
            "portugues": self._portuguese_activity,
            "ingles": self._english_activity,
            "espanhol": self._spanish_activity,
        }
        return handlers.get(discipline, self._generic_activity)(level, topic, difficulty)

    def evaluate(self, expected_answer, user_answer, discipline, topic):
        accepted_answers = [self._clean(answer) for answer in str(expected_answer).split("|")]
        clean_user = self._clean(user_answer)
        is_correct = clean_user in accepted_answers
        if is_correct:
            feedback = f"Resposta certa! Voce aplicou bem a ideia de {topic}."
        else:
            feedback = (
                f"A resposta esperada era '{str(expected_answer).split('|')[0]}'. Observe a palavra-chave do enunciado "
                f"e compare com o assunto {topic}."
            )
        return is_correct, feedback

    def _math_activity(self, level, topic, difficulty):
        if topic == "contagem":
            total = random.randint(2, 5 + difficulty)
            return self._short(f"Conte os objetos: {'* ' * total}Quantos tem?", str(total), "Aponte um por um e conte em voz alta.")
        if topic == "formas":
            shape, sides = random.choice([("triangulo", "3"), ("quadrado", "4"), ("retangulo", "4")])
            return self._short(f"Quantos lados tem um {shape}?", sides, "Conte cada lado da figura.")
        if topic == "maior e menor":
            a, b = self._numbers(level, difficulty)
            return self._short(f"Qual numero e maior: {a} ou {b}?", str(max(a, b)), "Compare quem aparece mais para frente na contagem.")
        if topic in ["numeros ate 20", "soma simples", "operacoes"]:
            a, b = self._numbers(level, difficulty)
            if difficulty >= 4:
                multiplier = random.randint(2, 9)
                return self._short(f"Resolva: {a} + {b} x {multiplier}", str(a + b * multiplier), "Resolva primeiro a multiplicacao.")
            if difficulty >= 3:
                total = a + b
                return self._short(f"Complete: {a} + ___ = {total}", str(b), "Descubra quanto falta para chegar ao total.")
            return self._short(f"Resolva a soma: {a} + {b}", str(a + b), "Some o segundo numero contando para frente.")
        if topic == "sequencias":
            start = random.randint(1, 8)
            step = random.choice([1, 2])
            return self._short(f"Complete a sequencia: {start}, {start + step}, {start + 2 * step}, ___", str(start + 3 * step), "Veja quanto aumenta de um numero para o outro.")
        if topic == "problemas":
            a, b = self._numbers(level, difficulty)
            stories = [
                (f"Maria tinha {a} figurinhas e ganhou {b}. Com quantas ficou?", a + b, "Quando ganha, a quantidade aumenta."),
                (f"Joao tinha {a + b} moedas e gastou {b}. Quantas sobraram?", a, "Quando gasta, a quantidade diminui."),
                (f"Uma caixa tem {a} fileiras com {min(b, 10)} lapis em cada. Quantos lapis ha no total?", a * min(b, 10), "Multiplique fileiras pela quantidade em cada uma."),
            ]
            question, answer, hint = random.choice(stories[: min(difficulty, len(stories))])
            return self._short(question, str(answer), hint)
        if topic == "tabuada":
            a = random.randint(2, min(5 + difficulty, 10))
            b = random.randint(2, 10)
            return self._short(f"Quanto e {a} x {b}?", str(a * b), "Multiplicacao e soma repetida.")
        if topic == "fracoes":
            if difficulty >= 4:
                denominator = random.choice([4, 5, 8, 10])
                numerator = random.randint(2, denominator - 1)
                return self._short(f"Em {numerator}/{denominator}, qual numero indica o total de partes iguais?", str(denominator), "O denominador fica embaixo.")
            total = random.choice([6, 8, 10, 12, 16])
            divisor = random.choice([2, 4])
            return self._short(f"Uma pizza foi dividida em {total} partes iguais. 1/{divisor} dela tem quantas partes?", str(total // divisor), "Divida o total pelo numero de baixo da fracao.")
        if topic == "porcentagem":
            percent, base = random.choice([(10, 100), (25, 80), (50, 60), (20, 150), (30, 200), (75, 120)])
            return self._short(f"Quanto e {percent}% de {base}?", str(int(base * percent / 100)), "Porcentagem e uma parte de 100.")
        if topic == "equacoes":
            x = random.randint(2, 12)
            add = random.randint(1, 10)
            return self._short(f"Resolva: x + {add} = {x + add}. Quanto vale x?", str(x), "Desfaca a soma subtraindo o mesmo valor.")
        if topic == "funcoes":
            x = random.randint(1, 8)
            a = random.randint(2, 5)
            b = random.randint(1, 9)
            return self._short(f"Na funcao f(x) = {a}x + {b}, quanto vale f({x})?", str(a * x + b), "Troque x pelo numero dado.")
        if topic == "probabilidade":
            return random.choice([
                self._choice("Em uma moeda comum, qual a chance de sair cara?", ["1/2", "1/3", "2/3", "1/4"], "1/2", "A moeda tem dois resultados possiveis."),
                self._choice("Em um dado comum, qual a chance de sair o numero 6?", ["1/6", "1/2", "2/6", "6/1"], "1/6", "O dado tem seis resultados possiveis."),
                self._choice("Em uma urna com 3 bolas azuis e 1 vermelha, qual cor e mais provavel sair?", ["azul", "vermelha", "as duas iguais", "nenhuma"], "azul", "Compare as quantidades de cada cor."),
            ])
        if topic == "geometria analitica":
            x1, y1 = random.randint(0, 5), random.randint(0, 5)
            distance = random.randint(2, 8)
            x2, y2 = x1 + distance, y1
            return self._short(f"Qual a distancia entre A({x1},{y1}) e B({x2},{y2})?", str(distance), "Como o y e igual, subtraia os valores de x.")
        return self._generic_activity(level, topic, difficulty)

    def _portuguese_activity(self, level, topic, difficulty):
        if topic == "vogais":
            word = random.choice(["aviao", "escola", "ilha", "ovo", "uva"])
            return self._short(f"Qual e a primeira vogal da palavra '{word}'?", word[0], "As vogais sao a, e, i, o, u.")
        if topic == "nomes e sons":
            word = random.choice(["bola", "casa", "mesa", "pato"])
            return self._short(f"A palavra '{word}' comeca com qual letra?", word[0], "Fale a palavra devagar.")
        if topic == "figuras e palavras":
            item = random.choice([("bola", ["bola", "copo", "livro", "sapato"]), ("casa", ["casa", "mesa", "pato", "dado"]), ("mala", ["mala", "lua", "peixe", "sol"])])
            return self._choice(f"Qual palavra combina com a figura de uma {item[0]}?", item[1], item[0], "Procure a palavra que nomeia o objeto.")
        if topic == "silabas":
            word, count, split = random.choice([("banana", "3", "ba-na-na"), ("cavalo", "3", "ca-va-lo"), ("sol", "1", "sol"), ("janela", "3", "ja-ne-la"), ("borboleta", "4", "bor-bo-le-ta")])
            return self._short(f"Quantas silabas tem a palavra '{word}'?", count, f"Separe assim: {split}.")
        if topic == "rimas":
            base, answer, options = random.choice([
                ("pato", "gato", ["gato", "mesa", "caderno", "sol"]),
                ("bola", "cola", ["cola", "janela", "pente", "livro"]),
                ("cafe", "chule", ["chule", "casa", "dado", "verde"]),
            ])
            return self._choice(f"Qual palavra rima com '{base}'?", options, answer, "Rima quando o final tem som parecido.")
        if topic == "leitura de palavras":
            return random.choice([
                self._choice("Qual palavra indica um animal?", ["cavalo", "janela", "lapis", "rua"], "cavalo", "Pense em seres vivos."),
                self._choice("Qual palavra indica um objeto escolar?", ["caderno", "gato", "chuva", "praia"], "caderno", "Pense no que usamos para estudar."),
                self._choice("Qual palavra indica um lugar?", ["escola", "azul", "correr", "feliz"], "escola", "Lugar e onde alguem pode estar."),
            ])
        if topic == "interpretacao de texto":
            items = [
                ("Lia pegou o guarda-chuva porque estava chovendo.", "Por que Lia pegou o guarda-chuva?", "porque estava chovendo"),
                ("Pedro estudou bastante e conseguiu resolver a prova.", "O que ajudou Pedro a resolver a prova?", "estudou bastante"),
                ("Ana fechou a janela quando o vento ficou forte.", "Quando Ana fechou a janela?", "quando o vento ficou forte"),
            ]
            text, prompt, answer = random.choice(items)
            return self._choice(f"Leia: '{text}' {prompt}", [answer, "porque estava com fome", "porque era noite", "porque perdeu o livro"], answer, "Procure a informacao diretamente no texto.")
        if topic == "substantivos":
            sentence, answer, options = random.choice([
                ("O menino chutou a bola", "menino", ["menino", "chutou", "O", "a"]),
                ("A professora abriu o livro", "professora", ["professora", "abriu", "A", "o"]),
                ("Meu cachorro dormiu cedo", "cachorro", ["cachorro", "dormiu", "cedo", "Meu"]),
            ])
            return self._choice(f"Na frase '{sentence}', qual palavra e um substantivo?", options, answer, "Substantivo nomeia pessoas, lugares, objetos ou ideias.")
        if topic == "pontuacao":
            return random.choice([
                self._choice("Qual sinal usamos no final de uma pergunta?", ["?", ".", ",", "!"], "?", "Perguntas precisam de ponto de interrogacao."),
                self._choice("Qual frase esta pontuada como pergunta?", ["Voce vem?", "Eu fui.", "Que susto!", "Comprei pao,"], "Voce vem?", "Perguntas terminam com ponto de interrogacao."),
                self._choice("Qual sinal pode separar itens em uma lista?", [",", "?", "!", ":"], ",", "A virgula ajuda a separar elementos."),
            ])
        if topic == "classes gramaticais":
            sentence, answer, options = random.choice([
                ("A menina correu rapidamente", "correu", ["correu", "menina", "rapidamente", "A"]),
                ("Os alunos leram o texto", "leram", ["alunos", "leram", "texto", "Os"]),
                ("A casa azul e bonita", "azul", ["azul", "casa", "e", "A"]),
            ])
            hint = "Verbo indica acao; adjetivo indica caracteristica."
            return self._choice(f"Na frase '{sentence}', qual palavra combina com a classe pedida pelo contexto?", options, answer, hint)
        if topic == "concordancia":
            sentence, answer, options = random.choice([
                ("Os alunos ___ atentos.", "estao", ["estao", "esta", "estava", "sou"]),
                ("A menina ___ feliz.", "esta", ["esta", "estao", "estamos", "sou"]),
                ("As professoras ___ a atividade.", "explicaram", ["explicaram", "explicou", "explica", "explico"]),
            ])
            return self._choice(f"Complete: '{sentence}'", options, answer, "Observe se o sujeito esta no singular ou plural.")
        if topic == "generos textuais":
            return random.choice([
                self._choice("Qual genero costuma trazer manchete e informacao de um fato?", ["noticia", "receita", "poema", "bilhete"], "noticia", "Pense em textos de jornal."),
                self._choice("Qual genero ensina ingredientes e modo de preparo?", ["receita", "conto", "noticia", "diario"], "receita", "Esse texto orienta como fazer algo."),
                self._choice("Qual genero costuma ter versos e ritmo?", ["poema", "manual", "noticia", "propaganda"], "poema", "Versos sao comuns em poemas."),
            ])
        if topic == "literatura":
            return random.choice([
                self._choice("Em um conto, quem vive as acoes da historia?", ["personagem", "rima", "paragrafo", "titulo"], "personagem", "Personagens participam da narrativa."),
                self._choice("O narrador de uma historia e quem:", ["conta os acontecimentos", "marca a pontuacao", "define a capa", "faz a rima"], "conta os acontecimentos", "Narrar e contar."),
                self._choice("O conflito em uma narrativa e:", ["o problema que movimenta a historia", "a lista de capitulos", "o nome da editora", "uma regra de acento"], "o problema que movimenta a historia", "Conflito cria tensao na historia."),
            ])
        if topic == "redacao":
            return random.choice([
                self._choice("Em uma redacao argumentativa, a tese e:", ["a opiniao principal defendida", "uma lista de compras", "o nome do autor", "um erro de pontuacao"], "a opiniao principal defendida", "A tese mostra o ponto de vista do texto."),
                self._choice("Qual parte costuma apresentar o tema e a tese?", ["introducao", "conclusao", "referencia", "titulo apenas"], "introducao", "A introducao abre o texto."),
                self._choice("Um argumento serve para:", ["defender a tese", "trocar o tema", "apagar a conclusao", "criar erro"], "defender a tese", "Argumentos sustentam a opiniao principal."),
            ])
        if topic == "analise sintatica":
            sentence, answer, options = random.choice([
                ("Os alunos estudaram matematica", "Os alunos", ["Os alunos", "estudaram", "matematica", "alunos estudaram"]),
                ("A enfermeira ajudou a crianca", "A enfermeira", ["A enfermeira", "ajudou", "a crianca", "enfermeira ajudou"]),
                ("Meu irmao leu o livro", "Meu irmao", ["Meu irmao", "leu", "o livro", "livro"]),
            ])
            return self._choice(f"Na frase '{sentence}', qual e o sujeito?", options, answer, "Pergunte quem praticou a acao.")
        return self._generic_activity(level, topic, difficulty)

    def _english_activity(self, level, topic, difficulty):
        maps = {
            "cores": [("red", "vermelho"), ("blue", "azul"), ("green", "verde")],
            "animais": [("dog", "cachorro"), ("cat", "gato"), ("bird", "passaro")],
            "cumprimentos": [("good morning", "bom dia"), ("hello", "ola"), ("good night", "boa noite")],
            "numeros": [("one", "um"), ("two", "dois"), ("ten", "dez")],
            "familia": [("mother", "mae"), ("father", "pai"), ("sister", "irma")],
            "objetos": [("book", "livro"), ("pencil", "lapis"), ("chair", "cadeira")],
            "rotina": [("I wake up", "eu acordo"), ("I study", "eu estudo"), ("I sleep", "eu durmo")],
        }
        if topic == "verbo to be":
            question, answer, hint = random.choice([
                ("Complete: I ___ a student.", "am", "Com 'I', usamos 'am'."),
                ("Complete: She ___ happy.", "is", "Com she, usamos 'is'."),
                ("Complete: They ___ friends.", "are", "Com they, usamos 'are'."),
            ])
            return self._choice(question, ["am", "is", "are", "be"], answer, hint)
        if topic == "perguntas simples":
            question, answer, options = random.choice([
                ("Qual frase significa 'Como voce esta?'", "How are you?", ["How are you?", "What color is it?", "Where is my book?", "I am happy."]),
                ("Qual frase pergunta 'Qual e o seu nome?'", "What is your name?", ["What is your name?", "How old are you?", "Where are you?", "I like blue."]),
                ("Qual frase pergunta 'Onde esta meu livro?'", "Where is my book?", ["Where is my book?", "What is this?", "How are you?", "My book is red."]),
            ])
            return self._choice(question, options, answer, "Procure a palavra principal da pergunta.")
        if topic == "simple present":
            question, answer, options = random.choice([
                ("Complete: She ___ soccer every day.", "plays", ["plays", "play", "played", "playing"]),
                ("Complete: They ___ English on Mondays.", "study", ["study", "studies", "studied", "studying"]),
                ("Complete: He ___ breakfast at 7.", "eats", ["eats", "eat", "ate", "eating"]),
            ])
            return self._choice(question, options, answer, "Observe o sujeito da frase.")
        if topic == "simple past":
            question, answer, options = random.choice([
                ("Qual e o passado de 'go'?", "went", ["went", "goed", "goes", "going"]),
                ("Qual e o passado de 'play'?", "played", ["played", "plays", "play", "playing"]),
                ("Complete: Yesterday, I ___ a movie.", "watched", ["watched", "watch", "watches", "watching"]),
            ])
            return self._choice(question, options, answer, "O simple past fala de acoes ja terminadas.")
        if topic in ["reading", "interpretacao"]:
            return self._choice("Text: 'Ana is hungry. She eats an apple.' Why does Ana eat?", ["because she is hungry", "because she is tired", "because she is late", "because she is cold"], "because she is hungry", "A primeira frase traz a causa.")
        if topic == "tempos verbais":
            return random.choice([
                self._choice("Em 'They are studying now', o tempo indica:", ["acao acontecendo agora", "acao no passado", "futuro distante", "ordem"], "acao acontecendo agora", "'Now' indica agora."),
                self._choice("Em 'I watched TV yesterday', a acao aconteceu:", ["no passado", "agora", "amanha", "sempre"], "no passado", "'Yesterday' indica passado."),
                self._choice("Em 'She will travel tomorrow', a acao indica:", ["futuro", "passado", "presente continuo", "habito"], "futuro", "'Will' e 'tomorrow' indicam futuro."),
            ])
        if topic == "argumentacao":
            return self._choice("Which connector introduces contrast?", ["however", "because", "and", "also"], "however", "Contrast mostra oposicao de ideias.")
        return self._translation_activity(maps.get(topic), topic)

    def _spanish_activity(self, level, topic, difficulty):
        maps = {
            "colores": [("rojo", "vermelho"), ("azul", "azul"), ("verde", "verde")],
            "saludos": [("buenos dias", "bom dia"), ("hola", "ola"), ("buenas noches", "boa noite")],
            "numeros": [("uno", "um"), ("dos", "dois"), ("diez", "dez")],
            "familia": [("madre", "mae"), ("padre", "pai"), ("hermana", "irma")],
            "objetos": [("libro", "livro"), ("lapiz", "lapis"), ("silla", "cadeira")],
            "comidas": [("manzana", "maca"), ("pan", "pao"), ("agua", "agua")],
            "verbos basicos": [("estudiar", "estudar"), ("leer", "ler"), ("comer", "comer")],
            "frases curtas": [("Tengo hambre", "estou com fome"), ("Buenos dias", "bom dia"), ("Me llamo Ana", "me chamo Ana")],
        }
        if topic == "leitura simples":
            return self._choice("Leia: 'Carlos bebe agua porque tiene sed.' Por que Carlos bebe agua?", ["porque tem sede", "porque tem sono", "porque perdeu o livro", "porque esta correndo"], "porque tem sede", "'Tiene sed' significa 'tem sede'.")
        if topic == "presente":
            question, answer, options = random.choice([
                ("Complete: Yo ___ espanol.", "estudio", ["estudio", "estudia", "estudian", "estudiar"]),
                ("Complete: Ella ___ en casa.", "vive", ["vive", "vivo", "viven", "vivir"]),
                ("Complete: Nosotros ___ agua.", "bebemos", ["bebemos", "bebe", "beben", "beber"]),
            ])
            return self._choice(question, options, answer, "Observe o sujeito da frase.")
        if topic == "preterito":
            return random.choice([
                self._choice("Qual frase esta no passado?", ["Ayer estudie.", "Hoy estudio.", "Manana estudiare.", "Estudiar es bueno."], "Ayer estudie.", "'Ayer' significa ontem."),
                self._choice("Complete: Ayer yo ___ una carta.", ["escribi", "escribo", "escribire", "escribir"], "escribi", "Ayer pede passado."),
                self._choice("Qual palavra indica passado?", ["ayer", "hoy", "manana", "ahora"], "ayer", "'Ayer' e ontem."),
            ])
        if topic == "interpretacion":
            return self._choice("Texto: 'Lucia esta cansada, por eso duerme.' O que Lucia faz?", ["dorme", "corre", "cozinha", "le"], "dorme", "'por eso' mostra a consequencia.")
        if topic == "lectura critica":
            return self._choice("Em uma leitura critica, o estudante deve:", ["avaliar ideias e intencoes do texto", "copiar sem pensar", "ignorar o contexto", "ler apenas o titulo"], "avaliar ideias e intencoes do texto", "Leitura critica vai alem de localizar palavras.")
        if topic == "conectores":
            return random.choice([
                self._choice("Qual conector indica causa?", ["porque", "pero", "aunque", "sin embargo"], "porque", "Causa explica o motivo."),
                self._choice("Qual conector indica oposicao?", ["pero", "porque", "tambien", "por eso"], "pero", "Oposicao contrasta ideias."),
                self._choice("Em 'Estudio porque quiero aprender', o conector mostra:", ["causa", "oposicao", "tempo", "lugar"], "causa", "'Porque' apresenta motivo."),
            ])
        if topic == "produccion textual":
            return self._choice("Antes de escrever um texto, e melhor:", ["planejar as ideias", "apagar o tema", "ignorar o leitor", "misturar qualquer assunto"], "planejar as ideias", "Planejamento organiza o texto.")
        return self._translation_activity(maps.get(topic), topic)

    def _translation_activity(self, pairs, topic):
        if not pairs:
            return self._generic_activity("fundamental_1", topic, 1)
        source, target = random.choice(pairs)
        return self._short(f"Traduza para portugues: '{source}'", target, "Pense no contexto do assunto escolhido.")

    def _generic_activity(self, level, topic, difficulty):
        return self._choice(
            f"Sobre '{topic}', qual atitude ajuda mais a aprender esse assunto?",
            ["ler o enunciado com atencao", "responder sem ler", "ignorar a dica", "trocar de assunto"],
            "ler o enunciado com atencao",
            "A melhor resposta e a que ajuda a entender o tema escolhido.",
        )

    def _numbers(self, level, difficulty):
        limits = {
            "maternal": 5,
            "infantil": 20,
            "fundamental_1": 50,
            "fundamental_2": 100,
            "medio": 150,
        }
        limit = limits.get(level, 30) + difficulty * 2
        return random.randint(1, limit), random.randint(1, limit)

    def _short(self, question, expected_answer, hint):
        return {
            "type": "short_answer",
            "question": self._with_context(question),
            "expected_answer": expected_answer,
            "hint": hint,
            "explanation": f"A resposta correta e '{expected_answer}' porque atende ao que o enunciado pediu.",
        }

    def _choice(self, question, options, expected_answer, hint):
        random.shuffle(options)
        return {
            "type": "multiple_choice",
            "question": self._with_context(question),
            "options": options,
            "expected_answer": expected_answer,
            "hint": hint,
            "explanation": f"'{expected_answer}' e a alternativa que corresponde ao enunciado.",
        }

    def _with_context(self, question):
        contexts = [
            "Atividade",
            "Questao de revisao",
            "Exercicio guiado",
            "Desafio rapido",
            "Pratica do assunto",
        ]
        return f"{random.choice(contexts)}: {question}"

    def _clean(self, value):
        normalized = unicodedata.normalize("NFD", str(value).lower().strip())
        without_accents = "".join(char for char in normalized if unicodedata.category(char) != "Mn")
        return " ".join(without_accents.split())
