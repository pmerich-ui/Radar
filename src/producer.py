from __future__ import annotations
import hashlib, json, math, os, sqlite3, subprocess, tempfile, wave
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

W,H,FPS=720,1280,30
CATALOG=[
("de","Beauty-Gadget","Live-Demo","DAS SOLL WIRKLICH FUNKTIONIEREN?!","Vorher-Nachher kritisch prüfen|Echte Bewertungen vergleichen|Preis und Rückgabe checken"),
("de","Küchen-Gadget","Problem-Lösung","ICH BRAUCHE DAS ... ODER DOCH NICHT?","Zeig zuerst das Alltagsproblem|Prüfe ob das Gadget hilft|Vergleiche den echten Endpreis"),
("de","Unboxing","Erwartung-Realität","BESTELLT VS. GELIEFERT!","Produktbilder kritisch prüfen|Grösse und Material kontrollieren|Rücksendung vorher klären"),
("de","Geschenk-Idee","Überraschung","DAS GESCHENK SIEHT TEUER AUS!","Nutzen statt Hype prüfen|Alternativen vergleichen|Budgetgrenze einhalten"),
("de","Preisvergleich","Rabatt-Falle","70 % RABATT?! Wirklich?","Alter Preis ist nicht Marktpreis|Vergleiche mehrere Shops|Prüfe den Endpreis"),
("de","Gratis Versand","Versand-Falle","GRATIS VERSAND ... ab 99 Franken?!","Mindestbestellwert beachten|Keine unnötigen Extras kaufen|Gesamtpreis vergleichen"),
("de","Black Friday","Kauf-Panik","BLACK FRIDAY: Kauf nicht blind!","Preisentwicklung prüfen|Wunschliste statt Impulskauf|Rückgaberegeln lesen"),
("de","Smartphone-Deal","Angebots-Check","HANDY 50 % BILLIGER? Moment!","Modell und Speicher vergleichen|Refurbished oder neu prüfen|Garantie und Versand beachten"),
("de","Schein-Schnäppchen","Shopping-Comedy","ICH HABE 200 FRANKEN GESPART ...","Rabatt ist keine Ersparnis ohne Bedarf|Nicht vom Countdown treiben lassen|Preis mit Alternativen vergleichen"),
("en","Smartphone deals","total cost","A cheap phone can cost more","Compare checkout total|Check warranty terms|Read return conditions"),
("de","Smartphone-Angebote","Endpreis","Handy-Schnäppchen? Achtung!","Endpreis inklusive Versand prüfen|Garantiebedingungen lesen|Rücksendekosten vergleichen"),
("en","Robot vacuums","maintenance","The hidden cost of robot vacuums","Check replacement brushes|Compare filter costs|Verify parts availability"),
("de","Saugroboter","Folgekosten","Saugroboter: Der Preis ist nicht alles","Kosten für Filter vergleichen|Ersatzteile prüfen|Garantie beachten"),
("en","Laptop shopping","upgrades","Before buying a laptop","Check memory upgrades|Compare storage options|Check repair and warranty terms"),
("de","Laptops","Aufrüstung","Laptop kaufen? Diese Punkte zählen","Erweiterbaren RAM prüfen|SSD-Varianten vergleichen|Garantiebedingungen beachten"),
("en","Headphones","fit","Earbuds: Three checks","Check device compatibility|Review fit and comfort|Check return rules"),
("de","Kopfhörer","Kompatibilität","Kopfhörer: Nicht blind kaufen","Gerätekompatibilität prüfen|Passform vergleichen|Rückgabebedingungen lesen"),
("en","Coffee machines","maintenance","Coffee machine deal?","Compare supply prices|Check maintenance costs|Review warranty terms"),
("de","Kaffeemaschinen","Unterhalt","Kaffeemaschine im Angebot?","Kosten für Entkalkung prüfen|Kaffee- und Filterpreise vergleichen|Wartungsbedarf prüfen"),
("en","Gaming bundles","components","Is the bundle actually cheaper?","Check each included item|Compare digital and physical games|Calculate the checkout total"),
("de","Konsolen-Bundles","Einzelpreise","Konsolen-Bundle: Guter Deal?","Einzelpreise vergleichen|Digitale und physische Spiele unterscheiden|Gesamtkosten berechnen"),
("en","Power banks","charging","Don't buy a power bank blind","Check the watt-hour rating|Review device compatibility|Verify safety certifications"),
("de","Powerbanks","Sicherheit","Powerbank kaufen? Achtung!","Wattstunden-Angabe prüfen|Anschlusskompatibilität prüfen|Sicherheitsangaben kontrollieren"),
("en","Running shoes","sizing","Buying running shoes online?","Check the brand's size guide|Compare return shipping fees|Review worn-item return rules"),
("de","Laufschuhe","Grösse","Schuhe online? Vermeide diese Fehler","Grössentabelle prüfen|Rücksendekosten vergleichen|Bedingungen für Anproben lesen"),
("en","Routers","updates","A cheap router is not always a deal","Verify update support|Confirm ISP compatibility|Check security settings"),
("de","Router","Updates","Router-Schnäppchen? Sicherheit zuerst","Sicherheitsupdates prüfen|Provider-Kompatibilität kontrollieren|Anschlüsse vergleichen"),
("en","Washing machines","energy","Compare more than the sticker price","Compare energy consumption|Check delivery and installation fees|Ask about removal costs"),
("de","Waschmaschinen","Betriebskosten","Waschmaschinen richtig vergleichen","Energieverbrauch prüfen|Liefer- und Montagekosten vergleichen|Altgeräteentsorgung beachten"),
("en","SSD storage","compatibility","Before buying a new SSD","Check the interface|Check physical form factor|Compare warranty coverage"),
("de","SSDs","Einbau","SSD-Angebote richtig prüfen","Schnittstelle kontrollieren|Baugrösse prüfen|Garantie vergleichen"),
("en","Monitors","display","Three monitor checks","Compare resolution at screen size|Check refresh rate and ports|Read pixel return terms"),
("de","Monitore","Bildschirm","Monitor im Angebot?","Auflösung prüfen|Bildfrequenz und Anschlüsse kontrollieren|Rückgabe bei Pixelfehlern prüfen")
]
FONTS=["/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf","/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"]
PALETTES=[("#071c2a","#13dcc0"),("#21112f","#ffc25b"),("#142725","#8bea9c"),("#251928","#ff9fbf")]
def font(size,bold=True):return ImageFont.truetype(FONTS[0 if bold else 1],size)
def split_lines(d,txt,ft,width):
    lines=[]; current=""
    for word in txt.split():
        option=(current+" "+word).strip()
        if d.textbbox((0,0),option,font=ft)[2]>width and current:lines.append(current);current=word
        else:current=option
    lines.append(current);return lines
def write(d,txt,x,y,width,size,color,bold=True):
    ft=font(size,bold)
    for line in split_lines(d,txt,ft,width):
        d.text((x,y),line,font=ft,fill=color);y+=int(size*1.32)
    return y
def slide(item,i,seed,path):
    lang,topic,angle,hook,facts=item
    bg,accent=PALETTES[(seed+i)%len(PALETTES)]
    im=Image.new("RGB",(W,H),bg);d=ImageDraw.Draw(im)
    for k in range(9):
        x=(seed//(k+1)+k*187+i*51)%W;y=(k*167+i*97)%H;r=35+(seed>>(k%11))%110
        d.ellipse((x-r,y-r,x+r,y+r),outline=accent,width=2)
    d.rounded_rectangle((38,45,682,132),radius=25,fill=accent)
    d.text((58,70),"DEALRADAR SCHWEIZ",fill=bg,font=font(26))
    if i==0:
        d.rounded_rectangle((42,235,678,820),radius=45,outline=accent,width=8)
        d.text((85,280),"SMART SHOPPING" if lang=="en" else "CLEVER KAUFEN",font=font(28),fill=accent)
        write(d,hook,80,395,550,64,"#ffffff")
        write(d,topic.upper(),80,750,550,30,accent)
    elif i==1:
        d.text((60,215),"3 QUICK CHECKS" if lang=="en" else "3 WICHTIGE CHECKS",font=font(45),fill=accent)
        for j,fact in enumerate(facts.split("|")):
            y=350+j*242
            d.rounded_rectangle((44,y,675,y+208),radius=25,outline=accent,width=4)
            d.ellipse((70,y+44,130,y+104),fill=accent)
            d.text((88,y+60),str(j+1),font=font(28),fill=bg)
            write(d,fact,158,y+37,465,33,"#ffffff",False)
    else:
        write(d,"CHECK BEFORE YOU BUY" if lang=="en" else "VOR DEM KAUF PRÜFEN",65,240,590,57,accent)
        d.rounded_rectangle((45,465,675,865),radius=35,outline=accent,width=7)
        write(d,facts.split("|")[(seed//37)%3],75,540,555,46,"#ffffff")
        d.rounded_rectangle((48,990,675,1110),radius=22,fill=accent)
        write(d,"Mehr Deals: DealRadar Schweiz",100,1025,530,26,bg)
    d.text((58,1200),"DealRadar Schweiz • Werbung",font=font(20),fill=accent)
    im.save(path)
def music(path,seconds,seed):
    rate=22050; notes=[110+seed%43,145+seed%31,180+seed%29,220+seed%37]
    with wave.open(str(path),"wb") as wf:
        wf.setnchannels(1);wf.setsampwidth(2);wf.setframerate(rate)
        chunk=bytearray()
        for n in range(rate*seconds):
            t=n/rate; k=int(t/1.5)%4; env=min(1,(t%1.5)/.08)*min(1,(1.5-t%1.5)/.23)
            val=(math.sin(2*math.pi*notes[k]*t)+.26*math.sin(4*math.pi*notes[k]*t))*.09*env
            chunk.extend(int(val*32767).to_bytes(2,"little",signed=True))
        wf.writeframes(chunk)
def validate(p):
    data=json.loads(subprocess.check_output(["ffprobe","-v","error","-show_entries","format=duration:stream=codec_name,codec_type,width,height,r_frame_rate,pix_fmt","-of","json",str(p)],text=True))
    v=next(x for x in data["streams"] if x.get("codec_type")=="video")
    duration=float(data["format"]["duration"]);n,d=map(int,v["r_frame_rate"].split("/"))
    if (v["width"],v["height"])!=(720,1280) or v["codec_name"]!="h264" or v["pix_fmt"]!="yuv420p" or not 23<=n/d<=60 or not 9<=duration<=20:raise ValueError("Video QA failed")
    digest=hashlib.sha256(p.read_bytes()).hexdigest()
    return {"fps":n/d,"duration":duration,"width":720,"height":1280,"sha256":digest}
def render(item,path):
    key="|".join(item);seed=int(hashlib.sha256(key.encode()).hexdigest()[:8],16)
    with tempfile.TemporaryDirectory() as folder:
        t=Path(folder);images=[t/f"{i}.png" for i in range(3)]
        for i,img in enumerate(images):slide(item,i,seed,img)
        audio=t/"original.wav";music(audio,12,seed)
        cmd=["ffmpeg","-hide_banner","-loglevel","error","-y"]
        for p in images:cmd+=["-loop","1","-framerate","30","-t","4","-i",str(p)]
        cmd+=["-i",str(audio)]
        f=";".join([f"[{i}:v]zoompan=z='min(zoom+0.0003,1.05)':d=120:s=720x1280:fps=30,trim=duration=4,setpts=PTS-STARTPTS[v{i}]" for i in range(3)]+["[v0][v1][v2]concat=n=3:v=1:a=0,format=yuv420p[v]"])
        cmd+=["-filter_complex",f,"-map","[v]","-map","3:a:0","-t","12","-c:v","libx264","-preset","ultrafast","-crf","26","-r","30","-pix_fmt","yuv420p","-c:a","aac","-b:a","96k","-movflags","+faststart",str(path)]
        subprocess.run(cmd,check=True,timeout=180)
    return validate(path)
def produce(root:Path):
    root.mkdir(parents=True,exist_ok=True)
    con=sqlite3.connect(root/"state.sqlite")
    con.execute("CREATE TABLE IF NOT EXISTS jobs(uid TEXT PRIMARY KEY,media_hash TEXT UNIQUE,status TEXT NOT NULL)")
    try:
        for item in CATALOG:
            uid=hashlib.sha256("|".join(item).encode()).hexdigest()[:24]
            if con.execute("SELECT 1 FROM jobs WHERE uid=?",(uid,)).fetchone():continue
            con.execute("INSERT INTO jobs(uid,status) VALUES(?,'RENDERING')",(uid,));con.commit()
            output=root/(uid+".mp4")
            qa=render(item,output)
            if con.execute("SELECT 1 FROM jobs WHERE media_hash=?",(qa["sha256"],)).fetchone():raise ValueError("Duplicate media detected")
            con.execute("UPDATE jobs SET status='VALIDATED',media_hash=? WHERE uid=?",(qa["sha256"],uid));con.commit()
            return {"id":uid,"language":item[0],"title":item[3],"file":str(output),"qa":qa,"status":"VALIDATED_NOT_PUBLISHED"}
        return {"status":"NO_NEW_BRIEFS"}
    finally:con.close()
if __name__=="__main__":
    print(json.dumps(produce(Path(os.environ.get("OUTPUT_DIR","./output"))),ensure_ascii=False))
