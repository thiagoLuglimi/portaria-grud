import shutil
from datetime import datetime
import os

# caminhos
DB_ORIGEM = 'database.db'
PASTA_BACKUP = r'S:/Meu Drive/backups_portaria'

# cria pasta se não existir
os.makedirs(PASTA_BACKUP, exist_ok=True)

# nome do arquivo com data
data = datetime.now().strftime('%Y-%m-%d_%H-%M')
destino = os.path.join(PASTA_BACKUP, f'database_backup_{data}.db')

# copia o banco
shutil.copy2(DB_ORIGEM, destino)

print(f'Backup criado: {destino}')
