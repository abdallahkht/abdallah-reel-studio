#!/usr/bin/env python3
"""Render original Arabic motion scenes. Pillow → FFmpeg, without a browser."""
import argparse
from functools import lru_cache
import json
from pathlib import Path
import shutil
import subprocess
import sys
from PIL import Image, ImageDraw, ImageFont
import arabic_reshaper
from bidi.algorithm import get_display

W,H=1080,1920

def ease(value):
    value=max(0,min(1,value))
    return 1-(1-value)**4


def find_font(value):
    if value:
        path=Path(value).expanduser()
        if not path.is_file():raise ValueError('Font file does not exist.')
        return str(path)
    candidates=[Path(__file__).resolve().parents[1]/'assets/fonts/IBMPlexSansArabic-Bold.ttf',Path('/System/Library/Fonts/Supplemental/Arial.ttf'),Path('C:/Windows/Fonts/arial.ttf'),Path('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf')]
    for path in candidates:
        if path.is_file():return str(path)
    raise ValueError('Pass --font with the path to an Arabic-capable TTF font.')


@lru_cache(maxsize=512)
def visual(text):
    return get_display(arabic_reshaper.reshape(str(text)))


@lru_cache(maxsize=256)
def font(path,size):
    # Reshaping and bidi already ran; BASIC avoids double shaping on RAQM builds.
    return ImageFont.truetype(path,max(12,int(size)),layout_engine=ImageFont.Layout.BASIC)


def label(draw,text,xy,path,size=64,color='#F4F5EF',width=880,anchor='mm'):
    text=visual(text)
    size=int(size)
    while size>20 and draw.textlength(text,font=font(path,size))>width:size-=2
    if draw.textlength(text,font=font(path,size))>width:
        raise ValueError('Text is too long. Shorten it or split the scene.')
    draw.text(xy,text,font=font(path,size),fill=color,anchor=anchor)


def frame(config,t,path):
    bg=config.get('background','#111510');accent=config.get('accent','#B8F36B')
    canvas=Image.new('RGB',(W,H),bg);d=ImageDraw.Draw(canvas)
    d.line((88,190,992,190),fill='#343A32',width=2)
    d.rounded_rectangle((88,105,101,145),radius=6,fill=accent)
    label(d,config.get('eyebrow',''),(978,125),path,28,'#B6BCB2',anchor='rm')
    d.line((88,1725,992,1725),fill='#343A32',width=2)
    label(d,config.get('footer',''),(88,1780),path,24,'#979E93',anchor='lm')
    progress=min(1,t/config['duration']);d.line((88,1725,88+904*progress,1725),fill=accent,width=4)
    kind=config['template']
    if kind=='title':
        reveal=ease((t-.12)/.65)
        d.rounded_rectangle((88,520,88+904*max(.001,reveal),534),radius=6,fill=accent)
        layer=Image.new('RGB',(W,H),bg);ld=ImageDraw.Draw(layer)
        label(ld,config['title'],(540,780+60*(1-reveal)),path,118,width=904)
        label(ld,config.get('subtitle',''),(540,950),path,57,'#B6BCB2')
        crop=layer.crop((0,620,W,1100));canvas.paste(Image.blend(Image.new('RGB',crop.size,bg),crop,reveal),(0,620))
        if t>.9:
            end=int(88+904*ease((t-.9)/.55));d=ImageDraw.Draw(canvas);d.line((88,1200,end,1200),fill=accent,width=3)
    elif kind=='metric':
        reveal=ease(t/.7);left=int(88+80*(1-reveal));right=992
        d.rounded_rectangle((left,440,right,1330),radius=40,fill='#202532',outline='#3B425A',width=2)
        label(d,config['title'],(540,550),path,60)
        label(d,config.get('value','3'),(540,850+60*(1-reveal)),path,310,accent)
        label(d,config.get('subtitle',''),(540,1160),path,50,'#BDC6E2')
        d.rounded_rectangle((150,1260,150+780*max(.001,ease((t-.6)/.8)),1270),radius=5,fill=accent)
    elif kind=='caption':
        words=config.get('words',['كل','كلمة','بوقتها'])
        active=min(len(words)-1,max(0,int((t-.25)/.65)))
        for i,word in enumerate(words):
            y=640+i*230
            if i==active:
                e=ease((t-.25-i*.65)/.35)
                d.rounded_rectangle((120,y-90,120+840*max(.001,e),y+100),radius=16,fill=accent)
            label(d,word,(540,y),path,146,bg if i==active else '#EBF0F5',width=820)
    elif kind=='compare':
        label(d,config['title'],(540,470),path,90)
        e=ease((t-.2)/.7)
        for i,(head,body) in enumerate(zip(config['labels'],config['items'])):
            y=650+i*375;offset=int((1-e)*(140 if i==0 else -140))
            d.rounded_rectangle((88+offset,y,992+offset,y+290),radius=22,fill='#172D3D' if i==0 else accent)
            label(d,head,(915+offset,y+66),path,38,'#89A5BC' if i==0 else '#153343',anchor='rm')
            label(d,body,(540+offset,y+180),path,68,'#F1F6FA' if i==0 else '#102839',width=790)
        d.line((540,960,540,1000),fill=accent,width=4)
    elif kind=='quote':
        e=ease((t-.2)/.8)
        d.rectangle((920,510,932,510+760*max(.001,e)),fill=accent)
        for i,line in enumerate(config['lines']):
            if t < .25+i*.3:continue
            label(d,line,(865,650+i*155),path,84,width=740,anchor='rm')
        if t>1.3:label(d,config.get('subtitle',''),(865,1260),path,38,'#A8BED1',width=740,anchor='rm')
    elif kind=='steps':
        label(d,config['title'],(540,460),path,88)
        for index,step in enumerate(config['steps']):
            reveal=ease((t-.35-index*.38)/.5)
            if reveal<=0:continue
            y=655+index*235;shift=int(60*(1-reveal))
            layer=Image.new('RGB',(W,210),bg);ld=ImageDraw.Draw(layer)
            ld.rounded_rectangle((88,5,992,205),radius=24,fill='#2A221D',outline='#514035',width=2)
            ld.ellipse((864,60,954,150),fill=accent)
            label(ld,str(index+1),(909,106),path,48,bg)
            label(ld,step,(820,106),path,49,width=680,anchor='rm')
            layer=Image.blend(Image.new('RGB',layer.size,bg),layer,reveal)
            canvas.paste(layer,(shift,y))
    return canvas


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('template',type=Path)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--font')
    parser.add_argument('--width',type=int,choices=[540,720,1080],default=1080)
    parser.add_argument('--fps',type=int,choices=[24,25,30,50,60],default=30)
    args=parser.parse_args()
    config=json.loads(args.template.read_text(encoding='utf-8'))
    if config.get('template') not in ['title','metric','steps','caption','compare','quote']:raise ValueError('Unknown template.')
    config['duration']=float(config.get('duration',4))
    if not 1<=config['duration']<=60:raise ValueError('Use a duration between 1 and 60 seconds.')
    if config['template']=='steps' and not 1<=len(config.get('steps',[]))<=3:raise ValueError('Use one to three short steps.')
    for kind,field in [('caption','words'),('quote','lines')]:
        if config['template']==kind and (not isinstance(config.get(field),list) or not 1<=len(config[field])<=3):raise ValueError(f'Use one to three entries in {field}.')
    if config['template']=='compare' and any(not isinstance(config.get(field),list) or len(config[field])!=2 for field in ['labels','items']):raise ValueError('Compare needs two labels and two items.')
    if not shutil.which('ffmpeg'):raise ValueError('Install FFmpeg first.')
    path=find_font(args.font);output=args.output.expanduser().resolve();poster=output.with_suffix('.png')
    if output.exists() or poster.exists():raise ValueError('Output exists. Choose a new name.')
    output.parent.mkdir(parents=True,exist_ok=True)
    width=args.width;height=width*16//9
    frame(config,min(2,config['duration']*.7),path).resize((width,height),Image.Resampling.LANCZOS).save(poster)
    process=subprocess.Popen(['ffmpeg','-v','error','-nostdin','-n','-f','rawvideo','-pix_fmt','rgb24','-s',f'{width}x{height}','-r',str(args.fps),'-i','-','-an','-c:v','libx264','-preset','veryfast','-crf','18','-pix_fmt','yuv420p','-movflags','+faststart',str(output)],stdin=subprocess.PIPE)
    try:
        for index in range(round(config['duration']*args.fps)):
            img=frame(config,index/args.fps,path).resize((width,height),Image.Resampling.LANCZOS)
            process.stdin.write(img.tobytes())
        process.stdin.close()
        if process.wait():raise ValueError('FFmpeg render failed.')
    except BaseException:
        process.stdin.close();process.wait();raise
    print(output)

if __name__=='__main__':
    try:main()
    except Exception as exc:print(str(exc),file=sys.stderr);sys.exit(1)
