
# Devolutiva formativa — Atividade 01 da SA

**Estudante:** Yann  
**Turma:** Rio Negrinho — Tarde  
**Unidade Curricular:** Programação de Aplicativos  
**Projeto escolhido:** Streaming de vídeo — Simulação interativa  
**Código analisado:** `codigo/app.py`  
**Referência:** Situação de Aprendizagem nº 1 — *Da Ideia ao Código*

## O que você já conseguiu desenvolver

Yann, você apresentou uma proposta criativa que combina uma simulação de transmissão ao vivo com elementos de jogo interativo. Seu projeto utiliza o Pygame e demonstra a aplicação de conceitos de programação gráfica, organização de estados e interação com o usuário.

Pontos positivos identificados:

- Utilizou **programação orientada a objetos** com a classe `JogoStreaming3D`.
- Implementou diferentes estados de interface e regras para alternar entre eles.
- Criou um ambiente gráfico com renderização, movimentação e tratamento de eventos.
- Desenvolveu mecanismos de pontuação, duração da sessão e indicadores de interação.
- Utilizou **funções, métodos, listas, estruturas condicionais, repetições e cálculos matemáticos**.
- Criou um fluxo inicial de cadastro e acesso ao ambiente interativo.
- Incluiu comentários que identificam vários blocos de funcionalidades.
- Tratou a ausência da biblioteca Pygame com uma mensagem que orienta sua instalação.

## O que precisa ser corrigido

### 1. Melhorar a proteção das credenciais

O sistema utiliza um arquivo `usuarios.txt` que armazena e recupera e-mails e senhas diretamente.

Esse formato não oferece proteção adequada às senhas.

**Como melhorar:** utilizar uma função apropriada para gerar e verificar hashes de senha, evitando armazenar as credenciais em texto simples. Também é importante não publicar arquivos preenchidos com dados de usuários.

### 2. Dividir o código em módulos menores

O arquivo `app.py` possui aproximadamente 1.500 linhas e concentra autenticação, renderização, estados, entrada de dados e regras de funcionamento.

**Como melhorar:** separar gradualmente as responsabilidades em módulos como autenticação, configuração, interface, renderização e regras da simulação. Essa divisão facilitará a localização de problemas e a manutenção.

### 3. Esclarecer a relação com o tema Streaming de Vídeo

O código simula uma transmissão ao vivo dentro de um jogo, mas não implementa diretamente uma plataforma para disponibilização ou reprodução de vídeos.

**Como melhorar:** descrever no README que se trata de uma **simulação interativa de streaming**, explicando como ela se relaciona com o problema escolhido. Caso o objetivo da SA seja uma plataforma de vídeos, identificar quais funcionalidades dessa plataforma ainda precisarão ser desenvolvidas.

## Oportunidades de melhoria

### 4. Documentar a instalação e a execução

O código informa como instalar o Pygame caso a biblioteca esteja ausente, mas o README ainda precisa conter instruções específicas do projeto.

**Como melhorar:** registrar a versão de Python utilizada, a dependência do Pygame, o comando para executar a aplicação e os controles disponíveis.

### 5. Melhorar a validação do cadastro

A validação do e-mail verifica apenas alguns caracteres básicos, e a senha é aceita com um comprimento mínimo reduzido.

**Como melhorar:** organizar as validações em funções específicas e melhorar as regras de cadastro, especialmente antes de disponibilizar o sistema fora de um ambiente de testes.

### 6. Organizar os cálculos e estados da simulação

O projeto possui diferentes variáveis para controlar tempo, pontuação, movimentação e condições da interface.

**Como melhorar:** agrupar configurações relacionadas, reduzir valores fixos espalhados pelo código e documentar as transições entre estados. Isso facilitará os ajustes sem comprometer outras partes do programa.

### 7. Ampliar os testes

A quantidade de funcionalidades aumenta a necessidade de verificar como elas interagem.

**Como melhorar:** testar o comportamento de cada estado, os limites dos cálculos, as entradas inválidas e as situações de encerramento e reinício.

## Testes recomendados

1. Executar o programa com a biblioteca Pygame instalada.
2. Verificar o cadastro e o acesso com dados válidos e inválidos.
3. Confirmar a movimentação e a interação com os elementos gráficos.
4. Testar a alternância entre telas e estados.
5. Verificar os cálculos de pontuação e tempo.
6. Testar a interrupção e o reinício da sessão.
7. Verificar o comportamento quando a biblioteca necessária não estiver disponível.

## Prioridades para a próxima versão

1. **Corrigir o armazenamento das senhas.**
2. **Separar as funcionalidades em módulos.**
3. **Explicar no README a relação entre a simulação e o tema Streaming de Vídeo.**
4. **Documentar dependências, comandos de execução e controles.**
5. **Registrar testes dos principais estados e funcionalidades.**

## Mensagem final

Yann, seu projeto demonstra iniciativa para explorar recursos além das operações básicas de terminal. Você aplicou **classes, métodos, cálculos, eventos e estruturas de controle** em uma aplicação interativa com diferentes funcionalidades.

O próximo passo é transformar essa complexidade em uma estrutura mais organizada, segura e fácil de testar. **Continue desenvolvendo sua criatividade, mas mantenha atenção à clareza das responsabilidades e à proteção das informações.** Essas práticas ajudarão você a construir aplicações cada vez melhores.
