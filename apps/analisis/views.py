from django.shortcuts import render
from django.contrib.auth.decorators import login_required

@login_required
def proses_analisis(request):
    return render(request, 'dashboard/proses_analisis.html', {'active': 'analisis'})