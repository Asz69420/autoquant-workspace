import subprocess,sys,json
out=subprocess.check_output([
 sys.executable,'scripts/pipeline/link_research_indicators.py',
 '--research-card-path','artifacts/research/20260224/research-20260224-6a4dd103b40d.research_card.json',
 '--indicator-record-paths',json.dumps(['artifacts/indicators/20260224/indicator-20260224-45403878d6e0.indicator_record.json'])
],text=True)
print(out.strip())
