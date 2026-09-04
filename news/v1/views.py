from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from news.models import DarkNews, Tags
from news.v1.serializers import DarkNewsSerializer, TagsSerializer
from rest_framework.pagination import PageNumberPagination
from django.db.models import Q

class NewsPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100

class LatestsNewsView(APIView):
    pagination_class = NewsPagination

    def get(self, request):
        news = DarkNews.objects.all().order_by('-created_at')
        paginator = self.pagination_class()
        paginated_news = paginator.paginate_queryset(news, request)
        serializer = DarkNewsSerializer(paginated_news, many=True, context={'request': request})
        return paginator.get_paginated_response(serializer.data)

class NewsDetailView(APIView):
    def get(self, request, pk):
        try:
            news = DarkNews.objects.get(pk=pk)
            serializer = DarkNewsSerializer(news, context={'request': request})
            return Response(serializer.data)
        except DarkNews.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

class LikeView(APIView):
    def post(self, request, pk):
        try:
            news = DarkNews.objects.get(pk=pk)
            news.likes += 1
            news.save()
            return Response({'likes': news.likes}, status=status.HTTP_200_OK)
        except DarkNews.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

class UnlikeView(APIView):
    def post(self, request, pk):
        try:
            news = DarkNews.objects.get(pk=pk)
            if news.likes > 0:
                news.likes -= 1
                news.save()
            return Response({'likes': news.likes}, status=status.HTTP_200_OK)
        except DarkNews.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

class DislikeView(APIView):
    def post(self, request, pk):
        try:
            news = DarkNews.objects.get(pk=pk)
            news.dislikes += 1
            news.save()
            return Response({'dislikes': news.dislikes}, status=status.HTTP_200_OK)
        except DarkNews.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

class UndislikeView(APIView):
    def post(self, request, pk):
        try:
            news = DarkNews.objects.get(pk=pk)
            if news.dislikes > 0:
                news.dislikes -= 1
                news.save()
            return Response({'dislikes': news.dislikes}, status=status.HTTP_200_OK)
        except DarkNews.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

class SearchView(APIView):
    pagination_class = NewsPagination

    def get(self, request):
        query = request.query_params.get('q', '')
        tag_name = request.query_params.get('tag', '')

        news = DarkNews.objects.all()

        if query:
            news = news.filter(Q(title__icontains=query) | Q(content__icontains=query))
        
        if tag_name:
            news = news.filter(tags__name__iexact=tag_name)

        news = news.order_by('-created_at')
        paginator = self.pagination_class()
        paginated_news = paginator.paginate_queryset(news, request)
        serializer = DarkNewsSerializer(paginated_news, many=True, context={'request': request})
        return paginator.get_paginated_response(serializer.data)

class TagsView(APIView):
    def get(self, request):
        tags = Tags.objects.all().order_by('?')
        serializer = TagsSerializer(tags, many=True)
        return Response(serializer.data)
