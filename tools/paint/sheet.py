from PIL import Image
fs=["menu","clear","gameover","victory","hud","intro00","intro04","intro09"]
W=Image.new("RGB",(4*260,2*260))
for i,f in enumerate(fs):
    im=Image.open(f"screens/{f}.png").convert("RGB").resize((256,256),Image.NEAREST); W.paste(im,((i%4)*260,(i//4)*260))
W.save("sheet.png")
