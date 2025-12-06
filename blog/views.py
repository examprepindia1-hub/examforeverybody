from django.shortcuts import render, get_object_or_404
from .models import Post
from django.core.paginator import Paginator

def post_list(request):
    # Get all published posts
    posts = Post.objects.filter(status='published')
    
    # Separate Featured Post (Top Story)
    featured_post = posts.filter(is_featured=True).first()
    if featured_post:
        posts = posts.exclude(id=featured_post.id)

    # Pagination
    paginator = Paginator(posts, 9) # 9 posts per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'blog/post_list.html', {
        'page_obj': page_obj,
        'featured_post': featured_post
    })

def post_detail(request, slug):
    post = get_object_or_404(Post, slug=slug, status='published')
    
    # Suggestions (Other recent posts)
    related_posts = Post.objects.filter(status='published').exclude(id=post.id)[:3]
    
    return render(request, 'blog/post_detail.html', {
        'post': post,
        'related_posts': related_posts
    })