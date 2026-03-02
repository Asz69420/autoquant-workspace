import subprocess,sys
src = """// © RedKTrader
//@version=5
indicator('RedK Trader Pressure Index (TPX)', shorttitle='RedK_TPX v5.0', overlay=false, timeframe='', precision=1)
length=input.int(title='Avg Length',defval=7,minval=1)
smooth=input.int(title='Smoothing',defval=3,minval=1)
clevel=input.int(title='Control Level',defval=30,minval=5,maxval=100)
R=ta.highest(2)-ta.lowest(2)
hiup=math.max(ta.change(high),0)
loup=math.max(ta.change(low),0)
bulls=math.min((hiup+loup)/R,1)*100
avgbull=ta.wma(nz(bulls),length)
hidn=math.min(ta.change(high),0)
lodn=math.min(ta.change(low),0)
bears=math.max((hidn+lodn)/R,-1)*-100
avgbear=ta.wma(nz(bears),length)
net=avgbull-avgbear
TPX=ta.wma(net,smooth)
"""
out = subprocess.check_output([
    sys.executable,'scripts/pipeline/emit_indicator_record.py',
    '--tv-ref','tv://script/v8sBugsW',
    '--url','https://www.tradingview.com/script/v8sBugsW-RedK-Trader-Pressure-Index-TPX-v1-0/',
    '--name','RedK Trader Pressure Index (TPX v1.0)',
    '--author','RedKTrader',
    '--version','v5.0',
    '--source-code',src,
    '--key-inputs','["Avg Length","Smoothing","Control Level","Pre-smoothing"]',
    '--signals','["Bull pressure","Bear pressure","Net pressure swing around zero"]',
    '--notes','["Matched via transcript hint + TradingView search in authenticated openclaw profile"]'
], text=True)
print(out.strip())
