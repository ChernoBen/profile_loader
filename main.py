import os
import time
import random
import json
import csv
import re
import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from webdriver_manager.chrome import ChromeDriverManager
import pandas as pd
from pathlib import Path
from datetime import datetime

# ——— Configurações globais ———
PROFILE_LIST = [
    "diarinho"
]
REELS_LIMIT  = 5
USERNAME     = "insta-user"
PASSWORD     = "insta-password"
BASE_URL     = "https://www.instagram.com"
API_URL      = "https://www.instagram.com/api/v1/feed/user/{}/?count={}"

def init_driver(profile_path: str) -> webdriver.Chrome:
    """Inicializa o driver do Chrome com configurações otimizadas"""
    os.makedirs(profile_path, exist_ok=True)
    options = Options()
    options.add_argument(f"--user-data-dir={profile_path}")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    
    # Configurações para evitar detecção
    for flag in [
        "--disable-notifications", 
        "--disable-infobars", 
        "--disable-extensions", 
        "--no-sandbox", 
        "--disable-gpu",
        "--disable-dev-shm-usage",
        "--disable-web-security",
        "--ignore-certificate-errors",
        "--start-maximized",
        "--disable-features=IsolateOrigins,site-per-process"
    ]:
        options.add_argument(flag)
        
    # User-Agent realista
    options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
    )
    
    # Configurar perfil para evitar login repetido
    options.add_argument("--disable-site-isolation-trials")
    
    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()), 
        options=options
    )
    
    # Configurações de stealth avançadas
    stealth_script = """
    Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
    Object.defineProperty(navigator, 'languages', {get: () => ['pt-BR','pt','en-US','en']});
    window.localStorage.setItem = function() {};
    window.sessionStorage.setItem = function() {};
    """
    driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {'source': stealth_script})
    
    # Timeouts aumentados
    driver.set_page_load_timeout(60)
    driver.set_script_timeout(60)
    
    return driver

def human_delay(a=1, b=3): 
    """Delay humano com variação aleatória"""
    time.sleep(random.uniform(a, b))

def is_logged_in(driver):
    """Verifica se o usuário está logado"""
    try:
        driver.get(f"{BASE_URL}/accounts/edit/")
        human_delay(2, 3)
        
        # Verifica múltiplos indicadores de login
        if "accounts/login" in driver.current_url:
            return False
            
        if driver.find_elements(By.XPATH, "//input[@name='firstName']"):
            return True
            
        if driver.find_elements(By.XPATH, "//a[contains(@href, 'logout')]"):
            return True
            
        return False
    except Exception as e:
        print(f"Erro na verificação de login: {str(e)}")
        return False

def perform_login(driver):
    """Realiza o login no Instagram com tratamento robusto"""
    print("Realizando login...")
    try:
        driver.get(f"{BASE_URL}/accounts/login/")
        human_delay(2, 3)
        
        # Verifica se já está logado
        if "accounts/login" not in driver.current_url:
            print("Já está logado!")
            return True
            
        # Preenche formulário de login
        username_field = WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.NAME, 'username'))
        )
        password_field = driver.find_element(By.NAME, 'password')
        
        # Preenchimento humano
        username_field.send_keys(USERNAME)
        human_delay(0.5, 1)
        password_field.send_keys(PASSWORD)
        human_delay(0.5, 1)
        
        # Clica no botão de login
        login_button = driver.find_element(By.XPATH, "//button[@type='submit']")
        login_button.click()
        
        # Verificação de login com timeout maior
        try:
            WebDriverWait(driver, 20).until(
                EC.any_of(
                    EC.presence_of_element_located((By.XPATH, "//div[text()='Home']")),
                    EC.presence_of_element_located((By.XPATH, "//span[contains(., 'Início')]")),
                    EC.presence_of_element_located((By.XPATH, "//img[contains(@alt, 'profile picture')]"))
                )
            )
            print("Login realizado com sucesso!")
            return True
        except TimeoutException:
            # Verifica se há desafio de segurança
            if driver.find_elements(By.XPATH, "//h1[contains(., 'Confirme')]"):
                print("Desafio de segurança detectado! Por favor resolva manualmente.")
                input("Pressione Enter após resolver o desafio...")
                return True
            else:
                print("Tempo excedido na verificação de login")
                return False
                
    except Exception as e:
        print(f"Falha no login: {str(e)}")
        return False

def get_session_cookies(driver):
    """Obtém cookies de sessão para usar em requests"""
    return {c['name']: c['value'] for c in driver.get_cookies()}

def get_user_id(driver,profile_name):
    """Obtém o ID do usuário através da página de perfil"""
    try:
        driver.get(f"{BASE_URL}/{profile_name}/")
        human_delay(3, 4)
        
        # Tenta encontrar o ID no JSON embutido
        script_content = driver.find_element(
            By.XPATH, 
            "//script[contains(text(), 'profilePage_')]"
        ).get_attribute("textContent")
        
        match = re.search(r'"profilePage_(\d+)"', script_content)
        if match:
            return match.group(1)
            
        # Fallback: Extrai de links alternativos
        links = driver.find_elements(By.XPATH, "//a[contains(@href, '/p/')]")
        if links:
            first_link = links[0].get_attribute("href")
            match = re.search(r"/p/([^/]+)/", first_link)
            if match:
                return match.group(1).split("_")[0]
                
    except Exception as e:
        print(f"Erro ao obter user ID: {str(e)}")
    
    return None

def get_reels_data_api(cookies, user_id):
    """Obtém dados de reels diretamente da API do Instagram"""
    if not user_id:
        return []
    
    url = API_URL.format(user_id, REELS_LIMIT * 2)
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
        "X-IG-App-ID": "936619743392459",
        "Accept": "application/json",
    }
    
    try:
        response = requests.get(url, headers=headers, cookies=cookies)
        response.raise_for_status()
        data = response.json()
        
        reels = []
        for item in data["items"]:
            if "video_versions" in item:  # Confirma que é um reel
                reel_data = {
                    "link": f"{BASE_URL}/reel/{item['code']}/",
                    "views": item.get("play_count", "N/A"),
                    "description": item.get("caption", {}).get("text", "N/A") if item.get("caption") else "N/A"
                }
                reels.append(reel_data)
                if len(reels) >= REELS_LIMIT:
                    break
        
        return reels
        
    except Exception as e:
        print(f"Erro na API: {str(e)}")
        return []

def extract_views_from_page(driver, url):
    """Tenta extrair visualizações da página como último recurso"""
    try:
        driver.get(url)
        human_delay(3, 4)
        
        # Método 1: Meta tag (dados estruturados)
        try:
            meta_element = driver.find_element(By.XPATH, "//meta[@property='og:video:views']")
            views = meta_element.get_attribute('content')
            if views:
                return int(views)
        except:
            pass
        
        # Método 2: Atributo aria-label
        try:
            element = driver.find_element(By.XPATH, 
                "//*[contains(@aria-label, 'views') or "
                "contains(@aria-label, 'visualizações')]"
            )
            aria_label = element.get_attribute('aria-label')
            match = re.search(r'[\d,.]+[KkMmBb]?', aria_label)
            if match:
                return extract_views_number(match.group())
        except:
            pass
        
        # Método 3: Texto visível
        try:
            elements = driver.find_elements(By.XPATH, 
                "//span[contains(., 'views') or contains(., 'visualizações')] | "
                "//div[contains(., 'views') or contains(., 'visualizações')]"
            )
            
            for elem in elements:
                text = elem.text.strip()
                match = re.search(r'[\d,.]+[KkMmBb]?', text)
                if match:
                    return extract_views_number(match.group())
        except:
            pass
    
    except Exception as e:
        print(f"Erro ao extrair views: {str(e)}")
    
    return "N/A"

def extract_views_number(views_text):
    """Converte texto de visualizações para número inteiro"""
    if isinstance(views_text, int):
        return views_text
        
    if not views_text or views_text == 'N/A':
        return "N/A"
    
    # Tenta converter diretamente se for string numérica
    try:
        return int(views_text)
    except:
        pass
    
    # Remove caracteres não numéricos, mantendo pontos e vírgulas
    clean_text = re.sub(r'[^\d,.]', '', str(views_text))
    
    if not clean_text:
        return "N/A"
    
    # Converte diferentes formatos numéricos
    try:
        # Formato com K/M/B (milhares/milhões/bilhões)
        multiplier = 1
        if 'K' in views_text or 'k' in views_text:
            multiplier = 1000
            clean_text = clean_text.replace('K', '').replace('k', '')
        elif 'M' in views_text or 'm' in views_text:
            multiplier = 1000000
            clean_text = clean_text.replace('M', '').replace('m', '')
        elif 'B' in views_text or 'b' in views_text:
            multiplier = 1000000000
            clean_text = clean_text.replace('B', '').replace('b', '')
        
        # Formato europeu: 1.000,00
        if '.' in clean_text and ',' in clean_text:
            clean_text = clean_text.replace('.', '').replace(',', '')
        # Formato americano: 1,000,000
        elif ',' in clean_text:
            clean_text = clean_text.replace(',', '')
        # Formato 1.000 (milhares)
        elif '.' in clean_text and len(clean_text.split('.')[-1]) == 3:
            clean_text = clean_text.replace('.', '')
        
        return int(float(clean_text) * multiplier)
    except Exception as e:
        print(f"Erro ao converter visualizações: '{views_text}' - {str(e)}")
        return views_text

def save_csv(data,output_csv):
    """Salva os dados em formato CSV"""
    with open(output_csv, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['link', 'description', 'views'])
        writer.writeheader()
        writer.writerows(data)
    print(f"Dados salvos em CSV: {output_csv}")

def save_json(data,output_json):
    """Salva os dados em formato JSON"""
    with open(output_json, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"Dados salvos em JSON: {output_json}")


def merge_and_save_profiles(dfs, output_path="profiles.csv"):
    """
    Concatena uma lista de DataFrames com as mesmas colunas
    e salva o resultado como profiles.csv.

    Parameters:
        dfs (list[pd.DataFrame]): Lista de DataFrames com as mesmas colunas
        output_path (str | Path): Caminho para salvar o CSV final

    Returns:
        pd.DataFrame: DataFrame resultante da concatenação
    """
    if not dfs:
        raise ValueError("A lista de DataFrames está vazia.")

    # Garante que todos tenham as mesmas colunas
    cols = dfs[0].columns
    for i, df in enumerate(dfs):
        if not all(df.columns == cols):
            raise ValueError(f"DataFrame na posição {i} tem colunas diferentes.")

    merged_df = pd.concat(dfs, ignore_index=True)
    time_now= datetime.now().strftime("%d/%m/%Y %H:%M:%S").replace("/","-").replace(" ","-")
    merged_df.to_csv(f"{time_now}-{output_path}", index=False, encoding="utf-8")
    print(f"Arquivo salvo em: {Path(output_path).resolve()}")
    return merged_df

def main(profile):
    print("🚀 Iniciando coleta de reels...")
    driver = init_driver('instagram_profile')
    reels_data = []
    
    try:
        # Verifica e realiza login
        if not is_logged_in(driver):
            print("🔑 Usuário não logado, iniciando login...")
            if perform_login(driver): 
                print("Login realizado com sucesso!")
            else:
                print("❌ Falha no login. Encerrando.")
                return
        else:
            print("🔑 Usuário já logado")
        
        # Obtém cookies de sessão
        cookies = get_session_cookies(driver)
        
        # Obtém user ID
        print("Obtendo ID do usuário...")
        user_id = get_user_id(driver,profile_name=profile)
        
        if not user_id:
            print("❌ Não foi possível obter o ID do usuário")
            return
        
        print(f"User ID encontrado: {user_id}")
        
        # Obtém dados via API
        print("Coletando dados via API...")
        reels_data = get_reels_data_api(cookies, user_id)
        
        # Se a API não retornou dados, tentar método de fallback
        if not reels_data:
            print("API não retornou dados, usando fallback...")
            driver.get(f"{BASE_URL}/{profile}/reels/")
            human_delay(5, 7)
            
            # Coleta links de reels
            reel_links = []
            try:
                links = WebDriverWait(driver, 20).until(
                    EC.presence_of_all_elements_located((By.XPATH, "//a[contains(@href, '/reel/')]"))
                )
                reel_links = [link.get_attribute('href') for link in links][:REELS_LIMIT]
            except:
                print("Não foi possível coletar links de reels")
            
            # Processa cada reel individualmente
            for link in reel_links:
                views = extract_views_from_page(driver, link)
                description = "N/A"
                
                # Tenta obter descrição
                try:
                    desc_element = driver.find_element(By.XPATH, 
                        "//h1[contains(@class, '_ap3a')] | "
                        "//div[contains(@class, '_a9zs')]"
                    )
                    description = desc_element.text.strip()
                except:
                    pass
                
                reels_data.append({
                    "link": link,
                    "views": views,
                    "description": description
                })
                human_delay(2, 3)
        
        # Salva resultados
        if reels_data:
            save_csv(reels_data,output_csv=f"./reports/{profile}.csv")
            save_json(reels_data,output_json=f"./reports/{profile}.json")
            print(f"\n✅ Coleta concluída! {len(reels_data)} reels processados")
        else:
            print("❌ Nenhum dado foi coletado")
            
    except Exception as e:
        print(f"\n❌ Erro durante execução: {str(e)}")
        # Tira screenshot para debug
        driver.save_screenshot('error_screenshot.png')
        print("📷 Screenshot salvo como error_screenshot.png")
        
    finally: 
        driver.quit()
        print("🛑 Navegador fechado")

if __name__ == '__main__': 
    [main(item) for item in PROFILE_LIST]
    profiles_data = [pd.read_csv(f"./reports/{item}.csv") for item in PROFILE_LIST]
    merge_and_save_profiles(profiles_data)
    