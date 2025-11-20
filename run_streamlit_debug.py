import sys
import debugpy
import streamlit.web.cli as stcli

# Porta per VS Code
debugpy.listen(5678)
print("Waiting for debugger to attach...")
debugpy.wait_for_client()  # attende il collegamento

sys.argv = ["streamlit", "run", "app.py"]
stcli.main()