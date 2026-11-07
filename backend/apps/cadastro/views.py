import subprocess

from django.http import HttpResponse


def ping(request):
    host = request.GET["host"]
    saida = subprocess.check_output(f"ping -c 1 {host}", shell=True)
    return HttpResponse(saida)
