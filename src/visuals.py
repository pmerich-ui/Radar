"""Original illustrated shopping scenes. No third-party video footage or logos."""
from PIL import Image, ImageDraw, ImageFont

INK = "#eaf8f1"
LIME = "#b7ff73"
CORAL = "#ff827a"
DARK = "#102322"

def shape(d,kind,x,y,scale=1):
    """Draw an original, recognisable product illustration at x,y."""
    s=scale
    def rect(a,b,c,e,fill,outline=None,width=4,r=16):
        pts=(int(x+a*s),int(y+b*s),int(x+c*s),int(y+e*s))
        d.rounded_rectangle(pts,radius=max(2,int(r*s)),fill=fill,outline=outline,width=max(1,int(width*s)))
    def line(points,fill=INK,width=6):
        d.line([(int(x+a*s),int(y+b*s)) for a,b in points],fill=fill,width=max(1,int(width*s)),joint="curve")
    if kind=="phone":
        rect(65,0,305,480,"#172a37",LIME,9,42)
        rect(87,42,283,411,"#265d75",None,1,14)
        d.ellipse((int(x+173*s),int(y+437*s),int(x+199*s),int(y+463*s)),fill=LIME)
        line([(110,316),(178,229),(249,276)],"#8fd4ee",12)
        rect(134,68,234,83,"#08151a",None,1,7)
    elif kind=="beauty":
        rect(115,72,255,450,"#efd4df",INK,5,36)
        rect(143,0,228,88,"#f58caa",INK,4,14)
        rect(148,210,224,300,"#fff6e8",None,1,12)
        d.ellipse((int(x+40*s),int(y+140*s),int(x+100*s),int(y+200*s)),fill=CORAL)
        d.ellipse((int(x+273*s),int(y+80*s),int(x+323*s),int(y+130*s)),fill=LIME)
    elif kind=="kitchen":
        rect(55,95,315,440,"#c7dbdf",INK,7,22)
        for j in range(5):
            for i in range(4):
                d.ellipse((int(x+(91+52*i)*s),int(y+(145+53*j)*s),int(x+(107+52*i)*s),int(y+(160+53*j)*s)),fill="#688e94")
        rect(105,10,266,86,"#ffba7f",INK,5,22)
        line([(315,330),(354,405)],LIME,15)
    elif kind in ("parcel","gift"):
        rect(27,140,348,453,"#dca468",INK,6,25)
        line([(185,140),(185,452)],"#805236",15)
        if kind=="gift":
            line([(27,235),(348,235)],CORAL,28)
            line([(185,141),(185,452)],CORAL,26)
            d.ellipse((int(x+104*s),int(y+40*s),int(x+195*s),int(y+146*s)),outline=CORAL,width=max(2,int(18*s)))
            d.ellipse((int(x+180*s),int(y+40*s),int(x+271*s),int(y+146*s)),outline=CORAL,width=max(2,int(18*s)))
        else:
            line([(27,142),(186,252),(348,142)],"#f6d6a7",18)
            rect(84,320,287,369,"#fff0cd",None,1,8)
    elif kind=="tag":
        d.polygon([(int(x+30*s),int(y+112*s)),(int(x+242*s),int(y+5*s)),(int(x+365*s),int(y+128*s)),(int(x+148*s),int(y+365*s)),(int(x+30*s),int(y+250*s))],fill=CORAL)
        d.ellipse((int(x+226*s),int(y+61*s),int(x+268*s),int(y+103*s)),fill=DARK)
        line([(247,79),(310,-3)],INK,8)
        for n in range(3):
            line([(125,168+n*52),(265,116+n*52)],"#793b3a",10)
    else:
        rect(30,60,334,420,"#d3e9e9",INK,7,30)
        rect(78,108,280,203,"#3d8f8d",None,2,12)
        rect(86,260,275,293,"#608e95",None,2,8)
        rect(86,323,226,355,"#608e95",None,2,8)

def product_kind(topic):
    low=topic.casefold()
    if any(t in low for t in ("beauty","kosmetik")):return "beauty"
    if any(t in low for t in ("küchen","kaffee")):return "kitchen"
    if any(t in low for t in ("unboxing","bestellt","geliefert","versand")):return "parcel"
    if any(t in low for t in ("geschenk",)):return "gift"
    if any(t in low for t in ("rabatt","black friday","preisvergleich","schnäppchen")):return "tag"
    return "phone"

def frame(image,item,stage,seed):
    """Render 3 illustrated video keyframes: hook, contrast, practical resolution."""
    lang,topic,angle,hook,facts=item
    d=ImageDraw.Draw(image)
    w,h=image.size
    for y in range(h):
        t=y/h
        d.line((0,y,w,y),fill=(int(10+11*t),int(30+17*t),int(34+8*t)))
    d.rounded_rectangle((35,39,685,113),radius=18,fill="#d4ff7c")
    fn=lambda size: ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",size)
    def lines(text,x,y,max_width,sz,color=INK):
        words=text.split();current="";ls=[]
        for word in words:
            test=(current+" "+word).strip()
            if d.textbbox((0,0),test,font=fn(sz))[2]>max_width and current:
                ls.append(current);current=word
            else:current=test
        ls.append(current)
        for l in ls[:5]:
            d.text((x,y),l,font=fn(sz),fill=color);y+=int(sz*1.35)
        return y
    d.text((56,57),"DEALRADAR SCHWEIZ",font=fn(29),fill=DARK)
    for k in range(7):
        xx=30+(seed//(k+3)+k*131)%665; yy=150+(k*173+seed//11)%990
        d.ellipse((xx,yy,xx+6,yy+6),fill="#355251")
    if stage==0:
        lines(hook,56,165,600,57,LIME)
        kind=product_kind(topic)
        d.rounded_rectangle((75,442,645,1058),radius=38,fill="#183e3c",outline="#4a6e65",width=3)
        shape(d,kind,200,515,.87)
        d.rounded_rectangle((110,952,609,1035),radius=20,fill=CORAL)
        lines("ECHT EIN DEAL?",140,967,440,32,DARK)
    elif stage==1:
        lines("ERWARTUNG  /  REALITÄT",40,161,640,42,LIME)
        d.rounded_rectangle((42,306,678,956),radius=28,fill="#173d3b")
        d.line((360,323,360,946),fill="#4a6862",width=5)
        kind=product_kind(topic)
        shape(d,kind,47,430,.74)
        shape(d,kind,370,470,.64)
        d.ellipse((84,347,147,410),fill=LIME)
        d.text((95,355),"+",font=fn(47),fill=DARK)
        d.ellipse((570,347,632,410),fill=CORAL)
        d.text((582,353),"?",font=fn(43),fill=DARK)
        lines("WAS KOSTET ES WIRKLICH?",58,1020,610,30,INK)
    else:
        facts3=facts.split("|")
        lines("3 CHECKS VOR DEM KAUF",45,163,640,44,LIME)
        for j,fact in enumerate(facts3):
            y=315+j*212
            d.rounded_rectangle((35,y,685,y+178),radius=23,fill="#20443f",outline="#4b6b62",width=3)
            d.rounded_rectangle((60,y+38,128,y+105),radius=17,fill=LIME)
            d.text((83,y+45),str(j+1),font=fn(39),fill=DARK)
            lines(fact,158,y+29,480,30,INK)
        d.rounded_rectangle((82,998,637,1107),radius=22,fill=LIME)
        lines("MEHR DEALS? FOLGE UNS.",111,1032,500,27,DARK)
    d.text((46,1219),"DealRadar Schweiz  ·  Werbung",font=fn(19),fill="#b5d3c3")
    return image
