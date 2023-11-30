from django.shortcuts import render
import json
from rest_framework.views import APIView

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
