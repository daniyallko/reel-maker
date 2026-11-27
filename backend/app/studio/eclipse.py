"""Offline direction for the solar eclipse explainer benchmark."""
from app.studio.schemas import Storyboard, StoryScene


def eclipse_motion(storyboard):
    from app.studio.motion import sanitize_motion_html
    return sanitize_motion_html(eclipse_html(storyboard))


def eclipse_board(sources, style, voice):
    shots = [
        ("A moving shadow", "See that shadow racing across Earth? It belongs to the Moon.", "Earth rotates beneath the Moon's shadow.", 0, 8),
        ("Three worlds align", "Pull back. The Moon slips between Earth and the Sun. Its shadow narrows.", "Reveal Sun, Moon and Earth and trace the shadow cone.", 8, 17),
        ("Two views", "At the edge, a crescent of sunlight remains. Near the center, the bright disk disappears.", "Compare the crescent Sun and totality side by side.", 17, 27),
        ("The corona", "Then, a faint halo. The corona.", "Hold on the solar corona around the dark Moon.", 27, 32),
    ]
    scenes = []
    delivery = ["Open with hushed curiosity. Lean on 'shadow', then let the discovery land.",
                "Invite the listener to pull back. Explain the alignment calmly, emphasizing 'between'.",
                "Build anticipation. Pause after the first sentence. Slow down on 'disappears'.",
                "Intimate, soft awe. Pause after 'halo'. Leave air after 'corona'."]
    for i, (title, line, action, start, end) in enumerate(shots):
        terms = ("shadow", "between", "partial", "corona")[i]
        ref = next((j for j, s in enumerate(sources) if terms in (s.claim + " " + s.title).lower()), 0)
        scenes.append(StoryScene(id=f"eclipse-{i}", start=start, end=end, headline=title, narration=line,
                                 delivery=delivery[i], tone=("curious", "measured", "building", "reflective")[i],
                                 visual_prompt=action, source_refs=[ref], layout="full_bleed"))
    return Storyboard(directed_motion=True, title="In the Moon’s shadow", style=style, voice=voice, duration=32, scenes=scenes,
                      sources=sources, speech_style="Quiet documentary narration with space between phrases.")


def eclipse_html(board):
    import json
    ends = json.dumps([s.end for s in board.scenes])
    return """<html><body style="margin:0;background:#060918"><canvas width="1080" height="1920"></canvas><script>
const c=document.querySelector('canvas').getContext('2d'), ends=ENDS;
function disk(x,y,r,color){c.fillStyle=color;c.beginPath();c.arc(x,y,r,0,2*Math.PI);c.fill()}
function glow(x,y,r){let g=c.createRadialGradient(x,y,r*.48,x,y,r);g.addColorStop(0,'#fff2cb');g.addColorStop(.55,'#ffd588');g.addColorStop(.7,'#e9914980');g.addColorStop(1,'#e9914900');disk(x,y,r,g)}
function earth(x,y,r,t){c.save();c.beginPath();c.arc(x,y,r,0,7);c.clip();let g=c.createRadialGradient(x-r*.4,y-r*.45,0,x,y,r);g.addColorStop(0,'#479ca6');g.addColorStop(.8,'#235773');g.addColorStop(1,'#09233c');disk(x,y,r,g);
for(let k=0;k<18;k++){c.fillStyle=k%3?'#83bcb05c':'#e1f5ed77';c.beginPath();for(let j=0;j<46;j++){let a=j/45*6.283,v=1+.28*Math.sin(5*a+k)+.18*Math.sin(9*a);let px=x+r*Math.sin(k*18+.06*t)+r*.22*Math.cos(a)*v,py=y+r*Math.cos(k*13)+r*.09*Math.sin(a)*v;j?c.lineTo(px,py):c.moveTo(px,py)}c.fill()}c.restore()}
function label(s,x,y,size=36){c.textAlign='center';c.font=size+'px sans-serif';c.fillStyle='#f3ebdb';c.fillText(s,x,y)}
window.seekTo=function(t){let i=ends.findIndex(e=>t<e);if(i<0)i=3;let a=i?ends[i-1]:0,p=Math.min(1,(t-a)/(ends[i]-a));c.fillStyle='#060918';c.fillRect(0,0,1080,1920);
for(let k=0;k<155;k++)disk((k*743)%1080,(k*k*113)%1920,k%3+.6,'#d7e4ed77');
if(i===0){earth(540,900,480,t);let x=260+560*p,y=850+85*p;let g=c.createRadialGradient(x,y,4,x,y,110);g.addColorStop(0,'#04091a');g.addColorStop(1,'#04091a00');disk(x,y,110,g)}
if(i===1){glow(540,425,230);earth(540,1190,225,t);let x=475+65*p;c.fillStyle='#a3a1b640';c.beginPath();c.moveTo(x-49,780);c.lineTo(x+49,780);c.lineTo(540,1015);c.fill();disk(x,780,48,'#797d89');label('SUN',820,440);label('MOON',752,790);label('EARTH',850,1200)}
if(i===2){for(let j=0;j<2;j++){let x=285+j*510;glow(x,900,218);disk(x+(j?3:90)-18*p,899,121,'#080b18');label(j?'TOTAL':'PARTIAL',x,1120)}}
if(i===3){let r=207+9*p;glow(540,900,r*1.92);for(let k=0;k<330;k++){let b=k*2.39996,l=r*(1.13+.48*Math.pow(Math.cos(b),6)+.12*Math.sin(k*71));c.strokeStyle='#ffe0ad22';c.beginPath();c.moveTo(540+r*Math.cos(b),900+r*Math.sin(b));c.quadraticCurveTo(540+l*Math.cos(b+.04),900+l*Math.sin(b+.04),540+l*Math.cos(b+.06),900+l*Math.sin(b+.06));c.stroke()}disk(540,900,r,'#060918')}
};window.seekTo(0)</script></body></html>""".replace("ENDS", ends)
