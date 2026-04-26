import urllib.request
import urllib.parse
import json
from bs4 import BeautifulSoup
import re
import time
import sys
import os

def get_page_data(wiki_domain, page_name):
    api_url = f"https://{wiki_domain}/api.php?action=parse&page={urllib.parse.quote(page_name)}&format=json"
    req = urllib.request.Request(api_url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
    try:
        response = urllib.request.urlopen(req).read()
        data = json.loads(response)
        if "error" in data:
            api_url = f"https://{wiki_domain}/api.php?action=parse&page={urllib.parse.quote(page_name + '_(episode)')}&format=json"
            req = urllib.request.Request(api_url, headers={"User-Agent": "Mozilla/5.0"})
            response = urllib.request.urlopen(req).read()
            data = json.loads(response)
        return data.get("parse", {}).get("text", {}).get("*", "")
    except Exception as e:
        return ""

def extract_images(html_content):
    soup = BeautifulSoup(html_content, 'html.parser')
    images = []
    for img in soup.find_all('img'):
        src = img.get('src', '')
        data_src = img.get('data-src', '')
        real_src = data_src if data_src else src
        if real_src and real_src.startswith('http') and 'Padlock' not in real_src and 'Real-world.png' not in real_src:
            clean_src = real_src.split('/revision/')[0] if '/revision/' in real_src else real_src
            if clean_src not in images:
                images.append(clean_src)
    return images

def extract_transcript(html_content):
    soup = BeautifulSoup(html_content, 'html.parser')
    dialogues = []
    tables = soup.find_all('table', class_='wikitable')
    for table in tables:
        rows = table.find_all('tr')
        for row in rows:
            cols = row.find_all(['th', 'td'])
            if len(cols) == 2:
                speaker = cols[0].get_text(separator=' ', strip=True)
                text = cols[1].get_text(separator=' ', strip=True)
                if speaker == "":
                    dialogues.append(f"[Action] {text}")
                else:
                    dialogues.append(f"{speaker}: {text}")
            elif len(cols) == 1:
                text = cols[0].get_text(separator=' ', strip=True)
                dialogues.append(f"[Action] {text}")

    cleaned_dialogues = []
    for d in dialogues:
        d = re.sub(r' \]', ']', d)
        d = re.sub(r'\[ ', '[', d)
        cleaned_dialogues.append(d)
    return cleaned_dialogues

def main():
    print("=====================================================")
    print(" FANDOM DIZI/FILM TRANSKRIPT VE GORSEL CEKICI BOT ")
    print("=====================================================")

    print("\nDIKKAT: Yapistiracaginiz link dizinin ANA SAYFASI degil, 'Bolum Listesi (List of episodes)' sayfasi olmalidir!")
    url = input("Link (Orn: https://avatar.fandom.com/wiki/List_of_Avatar:_The_Last_Airbender_episodes): ").strip()

    if not url:
        print("Link bos olamaz, cikis yapiliyor.")
        time.sleep(2)
        sys.exit()

    if "List_of_" not in url and "_episodes" not in url:
        print("\n[!] UYARI: Girdiginiz link bir 'Bolum Listesi' sayfasina benzemiyor.")
        print("    Eger sadece dizinin ana sayfasini girdiyseniz (ornegin: /wiki/The_Legend_of_Korra)")
        print("    bot yanlis tablolari okumaya calisip hata verebilir.")
        cevap = input("    Yine de devam etmek istiyor musunuz? (E/H): ").strip().lower()
        if cevap != 'e':
            sys.exit()

    try:
        parsed_url = urllib.parse.urlparse(url)
        wiki_domain = parsed_url.netloc
        path_parts = parsed_url.path.split("/wiki/")
        if len(path_parts) != 2:
            print("Gecersiz Fandom linki! Linkin /wiki/ formatinda oldugundan emin olun.")
            time.sleep(3)
            sys.exit()
        list_page_name = path_parts[1]
    except Exception as e:
        print(f"Linki cozumlerken hata olustu: {e}")
        time.sleep(3)
        sys.exit()

    print(f"\n[*] Site: {wiki_domain} | Sayfa: {urllib.parse.unquote(list_page_name)}")
    print("[*] Bolum listesi araniyor...\n")

    html_content = get_page_data(wiki_domain, list_page_name)
    if not html_content:
        print("[!] Sayfa icerigi bulunamadi. Lutfen linki kontrol edin.")
        time.sleep(3)
        sys.exit()

    soup = BeautifulSoup(html_content, 'html.parser')
    tables = soup.find_all('table', class_='wikitable')

    if not tables:
        print("[!] Bu sayfada herhangi bir bolum tablosu (wikitable) bulunamadi.")
        time.sleep(3)
        sys.exit()

    # Klasor olustur
    safe_show_name = list_page_name.replace("List_of_", "").replace("_episodes", "").replace("_", " ")
    safe_show_name = re.sub(r'[\\/*?:"<>|]', "", safe_show_name)
    if not os.path.exists(safe_show_name):
        os.makedirs(safe_show_name)

    season_idx = 1
    total_episodes_saved = 0
    for table in tables:
        rows = table.find_all('tr')
        if len(rows) < 5:
            continue

        print(f"\n---> SEZON {season_idx} Isleniyor...")
        ep_idx = 1

        for row in rows[1:]: # Basliklari atla
            cols = row.find_all(['th', 'td'])

            ep_title = ""
            for c in cols:
                # Cogu Fandom wiki'sinde bolum adlari tirnak icindedir. Tirnaklari arayalim.
                # Eger tirnak yoksa, a_tag'e bakalim ama yonetmenleri (orn Joaquim Dos Santos) ayiklamak icin
                # c'nin HTML metninde cift tirnak olup olmadigina bakabiliriz.

                # Cogu zaman bolum adi 'title' sutununda (genelde 2. veya 3. sutun) olur.
                # Bolum adlari genelde <a> tagi icindedir.
                a_tag = c.find('a')
                if a_tag:
                    title_text = a_tag.get('title', '')
                    # Gecersiz baglantilari (sayilar, kategoriler vb) filtrele
                    if title_text and not title_text.isnumeric() and 'Category' not in a_tag.get('href', '') and 'File:' not in a_tag.get('href', ''):
                        # Fandom listelerinde bolum ismi genellikle td/th icinde tirnak icine alinmistir.
                        text_content = c.get_text()
                        if '"' in text_content or "“" in text_content or "”" in text_content:
                            ep_title = title_text
                            break
                        # Veya table row sirasiyla ilk yazili metin ise (bazen tirnaksiz olabilir)
                        # Sadece daha guvenli olmasi acisindan sutunun bold veya sadece link icerdigine bakabiliriz.
                        if c.find('b') or len(c.get_text(strip=True)) == len(a_tag.get_text(strip=True)):
                            ep_title = title_text
                            break

            if not ep_title:
                continue

            clean_ep_title = ep_title.replace(" (episode)", "")
            print(f"  [{season_idx}x{ep_idx}] {clean_ep_title} indiriliyor...")

            transcript_page_name = f"Transcript:{ep_title.replace(' ', '_')}"

            main_html = get_page_data(wiki_domain, ep_title.replace(' ', '_'))
            images = extract_images(main_html)

            transcript_html = get_page_data(wiki_domain, transcript_page_name)
            dialogues = extract_transcript(transcript_html)

            if not dialogues:
                print(f"    -> [Uyari] '{clean_ep_title}' icin transkript metni bulunamadi. Atliyor.")
                continue

            # Dosyaya kaydet
            safe_file_title = re.sub(r'[\\/*?:"<>|]', "", clean_ep_title)
            filename = os.path.join(safe_show_name, f"S{season_idx}_Chapter_{ep_idx}_{safe_file_title}.txt")

            total_dialogues = len(dialogues)
            total_images = len(images)
            interval = max(1, total_dialogues // total_images) if total_images > 0 else total_dialogues + 1

            with open(filename, "w", encoding="utf-8") as f:
                f.write(f"S{season_idx}-Chapter {ep_idx}: {clean_ep_title}\n\n")
                img_idx = 0
                for i, d in enumerate(dialogues):
                    if img_idx < total_images and i > 0 and i % interval == 0:
                        f.write(f"![Image]({images[img_idx]})\n\n")
                        img_idx += 1
                    f.write(d + "\n\n")

            ep_idx += 1
            total_episodes_saved += 1
            time.sleep(0.5)

        season_idx += 1

    print(f"\n=====================================================")
    print(f" ISLEM TAMAMLANDI!")
    print(f" Toplam kaydedilen bolum: {total_episodes_saved}")
    print(f" Dosyalar '{safe_show_name}' klasorunde bulunmaktadir.")
    print(f"=====================================================")
    input("\nCikmak icin ENTER tusuna basin...")

if __name__ == "__main__":
    main()
