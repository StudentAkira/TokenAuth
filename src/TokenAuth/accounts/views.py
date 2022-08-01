import json, random
from django.core.paginator import Paginator
from django.shortcuts import render, redirect
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from .models import CustomUser, Profile, PostImage, Post
from rest_framework.response import Response
import requests
from .serializers import CustomUserSerializer, ProfileSerializer, PostSerializer, PostImageSerializer


class TokenLogin(APIView):
    def get(self, request):
        user = request.user
        username = request.user.username
        password = ''.join([random.choice('abcdefghijklmnopqrstuvwxyz') for i in range(20)])
        user.set_password(password)
        user.save()
        data = {
            'username': username,
            'password': password,
        }
        url = 'http://127.0.0.1:8000/auth/token/login'
        headers = {'Content-type': 'application/json'}
        response = requests.post(url, data=json.dumps(data), headers=headers)
        print(json.loads(response.text))
        token = json.loads(response.text)['auth_token']
        return redirect('http://127.0.0.1:3001/?token='+token)


class CheckAuth(APIView):
    def get(self, request):
        if not request.user.is_authenticated:
            return Response({'userId': -1})
        userId = request.user.id
        return Response({'userId': userId})


class ChangeAvatar(APIView):
    def post(self, request):
        print(request.data)
        print(request.data['avatar'])
        profile = request.user.profile
        profile.avatar.delete()
        profile.avatar = request.data['avatar']
        profile.save()
        return Response({'username': 'pass'})


class NewUserAPIView(APIView):
        def post(self, request):
            data = {
                'username':request.data['data']['username'],
                'password':request.data['data']['password']
            }
            new_user_serializer = CustomUserSerializer(data=data)
            new_user_serializer.is_valid()
            print(new_user_serializer.errors)
            new_user = new_user_serializer.create(validated_data=new_user_serializer.validated_data)
            return Response({'username': 'nothing'})


class CreateNewPostAPIView(APIView):
    def post(self, request):
        if not request.user.is_authenticated:
            return Response({'User':'unauthorizer'})

        data = request.data.dict()
        print(data)
        amount_of_images = len(data['ImageLocations'].split(','))-1
        print(amount_of_images)
        locations_of_images = data['ImageLocations'].split(',')
        if amount_of_images > 4:
            return Response({'error':'a lot of img'})

        new_post_serializer = PostSerializer(data=data)
        new_post_serializer.is_valid()
        post = new_post_serializer.create(validated_data=new_post_serializer.validated_data)
        post.owner = request.user
        post.save()

        for image_index in range(amount_of_images):
            PostImage.objects.create(
                image=data[f'image{image_index}'],
                position=locations_of_images[image_index],
                post=post,
            )

        return Response({'data':'data','user':'post'})


class GetPostAPIView(APIView):
    def get(self, request, pk):
        images = []
        post = Post.objects.prefetch_related('postimage_set').get(id=pk)
        for image_index in range(len(post._prefetched_objects_cache['postimage_set'])):
            images += [[
                        str(post._prefetched_objects_cache['postimage_set'][image_index].image),
                        str(post._prefetched_objects_cache['postimage_set'][image_index].position)
                      ]]

        print(images)
        post_serializer = PostSerializer(post)
        return Response({'images': images})


class GetPosts(APIView):
    def get(self, request, pk):
        posts_db = list(Post.objects.prefetch_related('postimage_set').all())
        paginator = Paginator(posts_db, 20)
        pagenumber = pk
        if pagenumber > len(paginator.page_range):
            pagenumber = len(paginator.page_range)
        paginated_posts = paginator.get_page(pagenumber)

        posts = []
        for post_index in range(len(list(paginated_posts))):
            post_serializer = PostSerializer(paginated_posts[post_index])
            posts += [[post_serializer.data, []]]
            for image in paginated_posts[post_index]._prefetched_objects_cache['postimage_set']:
                new_post_image_serializer = PostImageSerializer(image)
                posts[post_index][1] += [new_post_image_serializer.data]

        return Response({'PostsData':posts,'AmountOfPosts': len(posts_db)})


class GetUserAPIView(APIView):
    def get(self, request, pk):
        user = CustomUser.objects.get(id=pk)
        profile = Profile.objects.filter(user=user).get()
        print(profile.avatar)
        return Response({'username': user.username, 'avatar':str(profile.avatar)})


class GetUsers(APIView):
    def get(self, request, pk):
        users_db = list(CustomUser.objects.select_related('profile').all())
        paginator = Paginator(users_db, 20)
        pagenumber = pk
        if pagenumber > len(paginator.page_range):
            pagenumber = len(paginator.page_range)
        paginated_users = paginator.get_page(pagenumber)

        usersData = []
        for i in range(len(list(paginated_users))):
            user_serializer = CustomUserSerializer(paginated_users[i])
            profile_serializer = ProfileSerializer(paginated_users[i].profile)
            usersData += [[user_serializer.data, profile_serializer.data]]
        return Response({'UsersData': usersData, 'AmountOfUsers': len(users_db)})
