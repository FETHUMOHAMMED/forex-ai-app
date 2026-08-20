with open("ai-service/real_ai_service.py","r",encoding="utf-8") as f:
    content = f.read()
content = content.replace("self.blocked_pairs = {'USDCAD','NZDUSD','USDCHF','USDSGD','AUDUSD','EURJPY','GBPJPY','EURGBP','AUDJPY'}", 
                          "self.blocked_pairs = {'USDJPY','USDCAD','NZDUSD','USDCHF','USDSGD','AUDUSD','EURJPY','GBPJPY','EURGBP','AUDJPY'}")
with open("ai-service/real_ai_service.py","w",encoding="utf-8") as f:
    f.write(content)
print("Only GBPUSD + EURUSD allowed. USDJPY blocked.")
