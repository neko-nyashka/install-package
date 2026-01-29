import sys
import requests
from bs4 import BeautifulSoup
import subprocess
import os

KOJI_BASE_URL = "https://koji.fedoraproject.org"
KOJI_SEARCH_URL = KOJI_BASE_URL + "/koji/search?match=glob&type=package&terms="
KOJI_BUILDINFO_URL = KOJI_BASE_URL + "/koji/buildinfo?buildID="

def input_package():
    if len(sys.argv) < 2:
        print("Необходимо указать имя пакета")
        sys.exit(1)
    return sys.argv[1]

def search_package(package_name):
    print(f"Поиск пакета: {package_name}")
    build_candidates = []
    start = 0
    
    while True:
        url = f"{KOJI_SEARCH_URL}{package_name}&start={start}"
        try:
            response = requests.get(url)
            
            if response.status_code < 200 or response.status_code >= 300:
                print("Ошибка запроса статус-код:", response.status_code)
                return None
            
            soup = BeautifulSoup(response.text, "html.parser")
            rows = soup.find_all("tr", class_=["row-odd", "row-even"])
            
            if not rows:
                break
                
            for row in rows:
                td = row.find("td")
                if not td:
                    continue
                
                a = td.find("a", href=True)
                if a and "buildinfo?buildID=" in a["href"]:
                    build_id = a["href"].split("buildID=")[-1]
                    build_name = a.text.strip()
                    if ".fc" in build_name:
                        build_candidates.append((build_name, build_id))
            
            if soup.find("a", text="Next"):
                start += len(rows)
                print(f"Найдено сборок: {len(build_candidates)}...")
            else:
                break
                
        except Exception as e:
            print(f"Ошибка при поиске: {e}")
            break
    
    print(f"Всего найдено сборок: {len(build_candidates)}")
    return build_candidates

def choose_package(candidates):
    if not candidates:
        print("Пакеты не найдены.")
        return None

    page_size = 20
    current_page = 0
    total_pages = (len(candidates) + page_size - 1) // page_size
    
    while True:
        i1 = current_page * page_size
        i2 = min(i1 + page_size, len(candidates))
        page_candidates = candidates[i1:i2]
        
        print(f"\n=== Доступные сборки (страница {current_page + 1}/{total_pages}) ===")
        
        for i in range(len(page_candidates)):
            name = page_candidates[i][0]
            ind = i1 + i
            print(f"{ind + 1}. {name}")
        
        print("\nНавигация:")
        if current_page > 0:
            print("[P] - Предыдущая страница")
        if i2 < len(candidates):
            print("[N] - Следующая страница")
        print("[Q] - Выход")
        
        choice = input("\nВыберите пакет или действие: ").strip().lower()
        
        if choice == 'n' and i2 < len(candidates):
            current_page += 1
        elif choice == 'p' and current_page > 0:
            current_page -= 1
        elif choice == 'q':
            return None
        elif choice.isdigit():
            choice_ind = int(choice) - 1
            if 0 <= choice_ind < len(candidates):
                return candidates[choice_ind]
            print("Некорректный выбор. Введите номер из списка.")
        else:
            print("Некорректная команда. Введите номер пакета или команду навигации.")

def get_rpm_link(build_id):
    url = KOJI_BUILDINFO_URL + build_id
    try:
        response = requests.get(url)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, "html.parser")
        links = soup.find_all("a", href=True)
        
        rpm_links = []
        
        for link in links:
            href = link.get("href", "")
            if (href.endswith(".rpm") and  
                "/packages/" in href and 
                not href.endswith(".src.rpm") and  
                "aarch64" in href):
                rpm_links.append(href)
        
        if not rpm_links:
            raise ValueError(f"Бинарный RPM не найден.")
        
        for rpm in rpm_links:
            if "-debug" not in rpm:
                return rpm
        
        return rpm_links[0]
    
    except requests.RequestException as e:
        raise ValueError(f"Ошибка получения информации о сборке: {e}")

def is_installed(package_base_name):
    result = subprocess.run(
        ["rpm", "-qa", package_base_name + "*"], 
        capture_output=True,
        text=True
    )
    return bool(result.stdout.strip())

def download_and_install_rpm(rpm_url):
    filename = rpm_url.split("/")[-1]
    print(f"Скачиваем: {filename}")
    
    try:
        response = requests.get(rpm_url, stream=True)
        response.raise_for_status()
        
        with open(filename, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)

        print("Устанавливаем пакет...")
        result = subprocess.run(["sudo", "dnf", "install", "-y", filename])
        
        if result.returncode == 0:
            print("Пакет успешно установлен!")
        else:
            print("Ошибка установки пакета")
        
        return result.returncode == 0
    
    finally:
        if os.path.exists(filename):
            os.remove(filename)
            print(f"Временный файл удален: {filename}")

def main():
    package_name = input_package()
    
    candidates = search_package(package_name)
    if not candidates:
        print("Подходящие пакеты не найдены.")
        return

    chosen = choose_package(candidates)
    if not chosen:
        return
    
    chosen_name, build_id = chosen
    print(f"Выбран пакет: {chosen_name}")

    package_base_name = chosen_name.split('-')[0]

    if is_installed(package_base_name):
        answer = input("Пакет уже установлен. Удалить? (y/N): ").lower()
        if answer == 'y':
            print(f"Удаляем пакет: {package_base_name}")
            subprocess.run(["sudo", "dnf", "remove", "-y", package_base_name])
            sys.exit()

    try:
        rpm_url = get_rpm_link(build_id)
        
        if not rpm_url.startswith("http"):
            rpm_url = "https://kojipkgs.fedoraproject.org" + rpm_url
        
        print(f"RPM URL: {rpm_url}")
        
        download_and_install_rpm(rpm_url)
        
    except Exception as e:
        print(f"Ошибка: {e}")
        return

if __name__ == "__main__":
    main()