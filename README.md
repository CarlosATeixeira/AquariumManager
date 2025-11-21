# Simulador de Aquários Escolares

Aplicativo desktop em Python que incentiva o cuidado responsável com a vida aquática em ambientes educacionais. A experiência combina simulação em tempo real, acompanhamento de rotinas e conteúdo pedagógico alinhado à ODS 14 (Vida na Água).

## Visão geral

O software permite criar e administrar múltiplos aquários escolares, acompanhar indicadores como fome e saúde dos peixes, registrar rotinas de manutenção e utilizar um painel educativo para apoiar discussões em sala de aula. Toda a persistência é feita em SQLite, garantindo execução local e simples distribuição.

## Recursos principais

-   Gerenciamento simultâneo de vários aquários com ajuste fino de temperatura e limpeza.
-   Indicadores de bem-estar atualizados em tempo real para cada peixe cadastrado.
-   Visualizador gráfico animado construído com `PySide6`, reativo ao estado da simulação.
-   Sistema de rotinas recorrentes (alimentação, limpeza, temperatura e extras) com alertas de atraso.
-   Painel educativo com curiosidades contextuais sobre cada espécie registrada.

## Pré-requisitos

-   Windows 10 ou superior (funciona em outras plataformas que possuam Python 3.11+ e Qt).
-   Python 3.11 ou mais recente com `pip`.

## Instalação

1. (Opcional) Crie um ambiente virtual:
    ```
    python -m venv .venv
    .venv\Scripts\activate  # Windows
    source .venv/bin/activate  # Linux/macOS
    ```
2. Instale as dependências:
    ```
    pip install -r requirements.txt
    ```

## Execução

1. No diretório do projeto, execute:
    ```
    python main.py
    ```
2. O aplicativo inicializa com um aquário de demonstração armazenado em `aquarium.db`. Novos aquários, peixes e rotinas são persistidos automaticamente.

## Base de dados e persistência

-   O arquivo `aquarium.db` é criado no diretório raiz do projeto. Ele pode ser removido a qualquer momento para reiniciar o ambiente (um novo banco será populado ao abrir o aplicativo).
-   Para compartilhar o projeto sem dados locais, exclua `aquarium.db` e diretórios `__pycache__`.

## Testes automatizados

Execute a suíte de testes unitários com:

```
python -m unittest discover tests
```

## Estrutura do projeto

-   `main.py`: ponto de entrada do aplicativo e inicialização dos serviços.
-   `app/database.py`: camada de persistência e criação do banco SQLite.
-   `app/models.py`: modelos de dados (dataclasses) usados na simulação.
-   `app/simulation.py`: motor de regras e evolução dos estados do aquário.
-   `app/gui.py`: interface gráfica e interação com usuários.
-   `tests/`: casos de teste para a lógica central da simulação.

## Licença

Distribuído para uso educacional no âmbito das atividades extensionistas.
