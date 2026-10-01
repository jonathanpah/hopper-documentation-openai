"""Ocultação de padrões conhecidos de segredos.

Não garante detectar toda informação sensível.
"""

import base64
import json
import re

TEXT = {
    'hidden': '[oculto]',
    'credential_hidden': '[credencial oculta]',
    'key_hidden': '[chave privada oculta]',
}

KEY_BEGIN = re.compile('-----BEGIN [^-]*PRIVATE KEY(?: BLOCK)?-----')

KEY_END = re.compile('-----END [^-]*PRIVATE KEY(?: BLOCK)?-----')

KEY_FIELD = re.compile('(?i)(?<![a-z0-9_.-])(?:(?<!\\\\)(\\\\*[\\"\']))?([a-z0-9_.-]+)(\\\\*[\\"\'])?\\s*[:=]\\s*')

SENSITIVE_WORDS = {'password', 'passwd', 'senha', 'secret', 'credential', 'credencial', 'apikey', 'accesskey', 'privatekey'}

KEY_OWNERS = {'api', 'access', 'private', 'secret'}

VALUE_QUOTE = re.compile('(\\\\*)([\\"\'])')

BARE_VALUE = re.compile('(?![\\\\\\"\'\\[])[^\\s,;}\\]]+')

RANDOM_TOKEN = re.compile('(?<![A-Za-z0-9_+=/-])[A-Za-z0-9_+=-]{20,}(?![A-Za-z0-9_+=/-])')

TECHNICAL_PREFIXES = ('call_', 'fc_', 'msg_', 'toolu_', 'req_', 'resp_', 'chatcmpl-')

URL_CREDENTIAL = re.compile('(?i)(?<![a-z0-9+.-])([a-z][a-z0-9+.-]*://[^\\s:/@]+:)[^\\s@/]+(?=@)')

FLAG_KEY = re.compile('(?i)(?:(?<![\\w-])|(?<=\\\\[nrt]))--?(?:password|passwd|pass|token|secret|api[-_]?key)\\s+(?!-)')

SPOKEN_KEY = re.compile('(?i)(?:\\b|(?<=\\\\[nrt]))(?:senha|password|passwd)(?:\\s+\\S+){0,4}?\\s+(?:é|era|is|was)\\s+')

WORD = re.compile('\\S+')

TOKEN_START = re.compile('(?<![A-Za-z0-9_-])[A-Za-z0-9_-]+\\.')

TOKEN_REST = re.compile('[A-Za-z0-9_.-]*[A-Za-z0-9_-]')

FINGERPRINT = re.compile('(?i)(?:sha256|sha1|md5):$')

HEX_OR_UUID = re.compile('[0-9a-fA-F]+|[A-Za-z]{1,12}[0-9a-fA-F]{32,}|[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}')

def looks_random(token):
    if token.startswith(TECHNICAL_PREFIXES) or HEX_OR_UUID.fullmatch(token) or any((len(part) >= 5 and part.isalpha() and part.islower() for part in re.split('[-_]', token))):
        return False
    return sum((c.isupper() for c in token)) >= 3 and sum((c.islower() for c in token)) >= 3 and (sum((c.isdigit() for c in token)) >= 3)

def value_end(text, start, slashes, quote):
    """Posição do delimitador que fecha um valor aberto por `slashes` barras invertidas e `quote`.

    Cada nível de escape dobra as barras. Uma aspa precedida de n barras fecha o valor quando
    n % (2 * (slashes + 1)) == slashes; nos outros casos, ela faz parte do valor.
    """
    modulus = 2 * (slashes + 1)
    for i in range(start, len(text)):
        if text[i] == quote:
            n = 0
            while i - n - 1 >= start and text[i - n - 1] == '\\':
                n += 1
            if n % modulus == slashes:
                return i - slashes
    return len(text)

def mask(text):
    """Oculta credenciais em qualquer texto antes de enviá-lo, gravá-lo ou informá-lo."""
    text = hide_key_blocks(printable(text))
    parts, position = ([], 0)
    for key in KEY_FIELD.finditer(text):
        name = key.group(2)
        escaped = text[key.start(2) - 1:key.start(2)] == '\\'
        if key.start() < position or not (sensitive(name) or (escaped and sensitive(name[1:]))):
            continue
        quote = VALUE_QUOTE.match(text, key.end())
        if quote:
            parts.append(text[position:quote.end()] + TEXT['hidden'])
            position = value_end(text, quote.end(), len(quote.group(1)), quote.group(2))
            continue
        bare = BARE_VALUE.match(text, key.end())
        if bare:
            parts.append(text[position:key.end()] + TEXT['hidden'])
            position = bare.end()
    text = ''.join(parts) + text[position:]
    text = re.sub('(?i)\\b(?:sk|ghp|github_pat|xox[baprs])[-_][A-Za-z0-9_-]{8,}', TEXT['credential_hidden'], text)
    text = re.sub('(?i)(bearer\\s+)[A-Za-z0-9._~+/=-]{8,}', lambda m: m.group(1) + TEXT['hidden'], text)
    text = URL_CREDENTIAL.sub(lambda m: m.group(1) + TEXT['hidden'], text)
    text = re.sub('(?i)(authorization:\\s*basic\\s+)\\S+', lambda m: m.group(1) + TEXT['hidden'], text)
    text = hide_after(text, FLAG_KEY)
    text = hide_after(text, SPOKEN_KEY, looks_secret)
    text = re.sub('\\b(?:AKIA|ASIA)[A-Z0-9]{16}\\b', TEXT['credential_hidden'], text)
    text = hide_web_tokens(text)
    text = RANDOM_TOKEN.sub(hide_random, text)
    return text

def printable(text):
    """O texto sem surrogatos isolados nem bytes inválidos de nomes de arquivo, que o UTF-8 não grava."""
    return text.encode('utf-8', 'replace').decode('utf-8')

def sensitive(name):
    """Se um nome de campo rotula uma credencial, lido palavra por palavra: `db_password`, `apiKey`, `APIToken` e
    `API_TOKEN` rotulam; `max_tokens`, `token_count` e `desenhar` não."""
    spaced = re.sub('([a-z0-9])([A-Z])|([A-Z])([A-Z][a-z])', '\\1\\3_\\2\\4', name)
    words = [w.rstrip('0123456789') for w in re.split('[^a-z0-9]+', spaced.lower()) if w]
    return bool(words) and (any((w in SENSITIVE_WORDS for w in words)) or words[-1] == 'token' or any((a in KEY_OWNERS and b == 'key' for a, b in zip(words, words[1:]))))

def hide_random(match):
    """Oculta um segredo gerado. A impressão digital de uma chave (SHA256:…) é pública e fica."""
    if looks_random(match.group(0)) and (not FINGERPRINT.search(match.string, max(0, match.start() - 7), match.start())):
        return TEXT['credential_hidden']
    return match.group(0)

def hide_key_blocks(text):
    """Oculta cada bloco de chave privada, da linha de abertura até a próxima linha de fechamento."""
    parts, position = ([], 0)
    while True:
        begin = KEY_BEGIN.search(text, position)
        end = begin and KEY_END.search(text, begin.end())
        if not end:
            return ''.join(parts) + text[position:]
        parts.append(text[position:begin.start()] + TEXT['key_hidden'])
        position = end.end()

def hide_after(text, key, accept=None):
    """Oculta o valor depois de cada ocorrência de `key`: o valor inteiro entre aspas ou, sem aspas, a palavra seguinte
    se `accept` a aceitar."""
    parts, position = ([], 0)
    for found in key.finditer(text):
        if found.start() < position:
            continue
        quote = VALUE_QUOTE.match(text, found.end())
        if quote:
            start, end = (quote.end(), value_end(text, quote.end(), len(quote.group(1)), quote.group(2)))
        else:
            word = WORD.match(text, found.end())
            if not word or (accept and (not accept(word.group(0)))):
                continue
            start, end = (found.end(), word.end())
        parts.append(text[position:start] + TEXT['hidden'])
        position = end
    return ''.join(parts) + text[position:]

def hide_web_tokens(text):
    """Oculta JSON Web Tokens e valores assinados parecidos: segmentos base64url unidos por pontos, o primeiro deles
    um objeto JSON."""
    parts, position = ([], 0)
    for found in TOKEN_START.finditer(text):
        if found.start() < position or not json_object(found.group(0)[:-1]):
            continue
        rest = TOKEN_REST.match(text, found.end())
        if rest:
            parts.append(text[position:found.start()] + TEXT['credential_hidden'])
            position = rest.end()
    return ''.join(parts) + text[position:]

def json_object(segment):
    """Se um segmento base64url decodifica para um objeto JSON com ao menos um membro, com qualquer espaçamento."""
    try:
        value = json.loads(base64.urlsafe_b64decode(segment + '=' * (-len(segment) % 4)))
    except (ValueError, RecursionError):
        return False
    return isinstance(value, dict) and bool(value)

def looks_secret(value):
    value = value.rstrip('.,;:!?)')
    return len(value) >= 6 and any((not c.isalpha() for c in value))

def short(text):
    return mask(text)[-2000:]
