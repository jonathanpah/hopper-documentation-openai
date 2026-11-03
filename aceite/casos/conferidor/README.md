# Casos sintéticos do conferidor

Os textos seguem o Anexo E do SPEC.md, com a estrutura do conferidor do Anth
na tag v2.0.0. Nenhum arquivo foi produzido pelo plugin em teste.

| Pasta | Resultado esperado | Defeito deliberado |
| --- | --- | --- |
| valida | 9 aprovações; F9 não se aplica | Nenhum |
| valida-roteiro | 10 aprovações com o roteiro | Nenhum |
| valida-cabecalhos-no-corpo | 9 aprovações | Títulos e exemplo de cabeçalho dentro de uma mensagem |
| valida-campos-estruturados | 9 aprovações | Origens, intervalos, situações completas e item migrado válidos |
| valida-codigo-tilde | 9 aprovações | Código entre cercas de til, com fechamento maior que a abertura |
| valida-codigo-indentado | 9 aprovações | Código com 4 espaços e tabulação |
| valida-secoes-contiguas | 9 aprovações | As 9 seções sem linha vazia entre texto e título |
| valida-ancoras | 9 aprovações | Âncoras de título, título repetido e identificador HTML |
| invalida-F1 | Só F1 reprova | Falta o handoff da conversa migrada |
| invalida-F2 | Só F2 reprova | O registro t1/r3 aparece em 2 mensagens |
| invalida-F3 | Só F3 reprova | Falta a linha de assunto do primeiro bloco |
| invalida-F4 | Só F4 reprova | Situação não permitida em uma decisão |
| invalida-F5 | Só F5 reprova | Falta a seção Lacunas do handoff |
| invalida-F6 | Só F6 reprova | Link do índice aponta um arquivo ausente |
| invalida-F7 | Só F7 reprova | Uma frase tem 41 palavras |
| invalida-F8 | Só F8 reprova | O handoff cita D999, que não existe |
| invalida-F9 | Só F9 reprova com o roteiro | O item D registra verde em vez de azul |
| invalida-F10 | Só F10 reprova | Existe .state na raiz |
| invalida-F2-evento-registro | Só F2 reprova | Evento usa registro nativo em vez de status |
| invalida-F2-status-sem-evento | Só F2 reprova | Autor Codex usa o marcador status |
| invalida-F2-evento-turnos | Só F2 reprova | Os limites do Evento pertencem a turnos diferentes |
| invalida-F2-comentario | Só F2 reprova | Comentário de registros sem a barra obrigatória |
| invalida-F4-origem | Só F4 reprova | Origem sem identificador nem nome de arquivo antigo |
| invalida-F4-intervalo | Só F4 reprova | Intervalo sem mensagens |
| invalida-F4-intervalo-invertido | Só F4 reprova | Fim do intervalo anterior ao início |
| invalida-F4-revogacao | Só F4 reprova | Revogação sem mensagem válida |
| invalida-F4-desfeita | Só F4 reprova | Função desfeita sem mensagem válida |
| invalida-F4-encerramento | Só F4 reprova | Encerramento sem motivo |
| invalida-F4-sufixo | Só F4 reprova | Situação fixa com sufixo indevido |
| invalida-F4-substituicao | Só F4 reprova | Substituição sem identificador válido |
| invalida-F6-ancora | Só F6 reprova | Arquivo existe, mas a âncora não existe |
| invalida-F7-paragrafo | Só F7 reprova | Parágrafo com 7 frases curtas |

Todas as pastas têm 1 conversa regular e 1 conversa migrada. No caso F1,
`.keep` preserva no Git a pasta sem o handoff. Os outros documentos continuam
presentes, para que as demais verificações tenham objetos válidos.

Os nomes com sufixo mantêm o identificador da verificação após `invalida-`.
O workflow percorre todos os casos e exige apenas essa reprovação em cada um.

O caso com roteiro contém as 6 mensagens de F-C. A resposta ao pedido também
está copiada, mas a cobertura dos documentos 1, 3 e 7 termina no próprio pedido.
Isso exercita a comparação de F3 sem exigir que a cópia da resposta já tenha
entrado no bloco simplificado.

Execute da raiz do repositório.

```sh
python3 aceite/conferir.py aceite/casos/conferidor/valida --idioma pt-br
python3 aceite/conferir.py aceite/casos/conferidor/valida-roteiro --idioma pt-br --roteiro aceite/roteiro.json
python3 aceite/conferir.py aceite/casos/conferidor/invalida-F9 --idioma pt-br --roteiro aceite/roteiro.json
```
