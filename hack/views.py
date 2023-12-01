from django.shortcuts import render
import json
from rest_framework.views import APIView
import logging
import sys

logger = logging.getLogger(__name__)


# Create your views here.


class StartIndexingAPI(APIView):
    def post(self, request, *args, **kwargs):
        response = {}
        response['status'] = 500
        try:
            data = request.data["Request"]
            data = json.loads(data)

            perform_indexing_on_data('settings.BASE_DIR + pdf_search_obj.file_path')

        except Exception as e:
            print(e)

StartIndexing = StartIndexingAPI.as_view()


def TestPage(request):
    try:

        logger.info("testing logs.", extra={'AppName': 'hack'})

        return render(request, 'hack/test.html', {
            'year': '2023'
        })

    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        logger.error("ECCTimeLine %s at %s",
                     str(e), str(exc_tb.tb_lineno), extra={'AppName': 'hack'})
        # return HttpResponse("500")
        return render(request, 'EasyChatApp/error_500.html')
