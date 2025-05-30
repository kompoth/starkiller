#~/bin/bash
pipx uninject python-lsp-server starkiller
echo "Removed old Starkiller"

uv build
echo "New version ready"

WHEEL=`ls ./dist/starkiller-*-none-any.whl | sort -V | tail -1`
pipx inject python-lsp-server ${WHEEL}[pylsp] -f
echo "Installed ${WHEEL}"
