````markdown
# 📌 Configuração e Execução da Aplicação

## 🇧🇷 Como configurar o app
1. Certifique-se de estar usando **Python 3.9** ou **3.10**.  
2. Crie um ambiente virtual via terminal:  
   ```bash
   python -m venv env
````

3. Ative o ambiente virtual:
   **Windows**

   ```bash
   env\Scripts\activate
   ```

   **Linux/Mac**

   ```bash
   source env/bin/activate
   ```
4. Instale as dependências:

   ```bash
   pip install -r requirements.txt
   ```
5. No arquivo `main.py`, linhas **25** e **26**, defina o usuário e senha da conta que será utilizada para ler os perfis:

   ```python
   USERNAME = "insta-user"
   PASSWORD = "insta-password"
   ```
6. Na linha **21** do arquivo `main.py`, defina a lista de **@** que serão carregados pela aplicação.

## 🇧🇷 Como rodar a aplicação

```bash
python main.py
```

### 📄 Saída gerada

Após a execução do arquivo `main.py`, será criado um arquivo com nomenclatura no padrão:

```
dia-mes-ano-hora:minuto:segundo-profiles.csv
```

Esse arquivo conterá os dados dos perfis processados pelo algoritmo.

---

## 🇺🇸 How to configure the app

1. Make sure you are using **Python 3.9** or **3.10**.
2. Create a virtual environment via terminal:

   ```bash
   python -m venv env
   ```
3. Activate the virtual environment:
   **Windows**

   ```bash
   env\Scripts\activate
   ```

   **Linux/Mac**

   ```bash
   source env/bin/activate
   ```
4. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```
5. In the `main.py` file, lines **25** and **26**, set the username and password for the account that will be used to read profiles:

   ```python
   USERNAME = "insta-user"
   PASSWORD = "insta-password"
   ```
6. On line **21** of the `main.py` file, define the list of **@** that will be loaded by the application.

## 🇺🇸 How to run the application

```bash
python main.py
```

### 📄 Generated output

After running the `main.py` file, a file will be created following the naming pattern:

```
day-month-year-hour:minute:second-profiles.csv
```

This file will contain the data of the profiles processed by the algorithm.
