# serializers.py:
from rest_framework import serializers
from news.models import DarkNews, Tags

class TagsSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tags
        fields = ['id', 'name']

class DarkNewsSerializer(serializers.ModelSerializer):
    tags = TagsSerializer(many=True, read_only=True)
    url = serializers.HyperlinkedIdentityField(
        view_name='news_detail',
        lookup_field='pk'
    )

    class Meta:
        model = DarkNews
        fields = ['id', 'title', 'content', 'created_at', 'likes', 'dislikes', 'url', 'tags']