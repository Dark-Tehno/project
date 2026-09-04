from django.urls import path
from news.v1 import views


# API для Dark.News:
urlpatterns = [
    path('latests_news/', views.LatestsNewsView.as_view(), name='latests_news'),
    path('news_detail/<int:pk>/', views.NewsDetailView.as_view(), name='news_detail'),
    path('like/<int:pk>/', views.LikeView.as_view(), name='like'),
    path('unlike/<int:pk>/', views.UnlikeView.as_view(), name='unlike'),
    path('dislike/<int:pk>/', views.DislikeView.as_view(), name='dislike'),
    path('undislike/<int:pk>/', views.UndislikeView.as_view(), name='undislike'),
    path('search/', views.SearchView.as_view(), name='search'),
    path('tags/', views.TagsView.as_view(), name='tags'),
]