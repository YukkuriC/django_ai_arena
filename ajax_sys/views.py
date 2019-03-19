from django.shortcuts import render

def message_update(request):
    return render(request,'sub/messages.html')