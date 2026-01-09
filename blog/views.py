from django.shortcuts import render, get_object_or_404
from .models import Post
from core.models import Category
from django.contrib.auth import get_user_model
from django.db.models import Count, Q
from django.core.paginator import Paginator

def post_list(request):
    # Base Query
    posts = Post.objects.filter(status='published')
    
    # 1. Search
    query = request.GET.get('q')
    if query:
        posts = posts.filter(
            Q(title__icontains=query) |
            Q(content__icontains=query) |
            Q(tags__icontains=query)
        ).distinct()

    # 2. Filter by Category
    category_slug = request.GET.get('category')
    if category_slug:
        posts = posts.filter(categories__slug=category_slug)

    # 3. Filter by Author
    author_id = request.GET.get('author')
    if author_id:
        posts = posts.filter(author__id=author_id)

    # 4. Sorting
    sort_by = request.GET.get('sort', 'newest')
    if sort_by == 'popular':
        posts = posts.order_by('-views')
    else:
        posts = posts.order_by('-created_at')

    # Separate Featured Post (Only if on first page and no filters applied)
    featured_post = None
    if not query and not category_slug and not author_id and sort_by == 'newest':
         featured_post = posts.filter(is_featured=True).first()
         if featured_post:
             posts = posts.exclude(id=featured_post.id)

    # Sidebar Data: Categories with post counts
    categories = Category.objects.annotate(
        post_count=Count('posts', filter=Q(posts__status='published'))
    ).filter(post_count__gt=0).order_by('display_name')

    # Sidebar Data: Authors with post counts
    User = get_user_model()
    authors = User.objects.annotate(
        post_count=Count('post', filter=Q(post__status='published'))
    ).filter(post_count__gt=0).order_by('first_name')

    # Pagination
    paginator = Paginator(posts, 9) 
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'blog/post_list.html', {
        'page_obj': page_obj,
        'featured_post': featured_post,
        'categories': categories,
        'authors': authors,
        'query': query,
        'selected_category': category_slug,
        'selected_author': author_id,
        'sort_by': sort_by
    })

def post_detail(request, slug):
    post = get_object_or_404(Post, slug=slug, status='published')
    
    # Increment View Count (Primitive approach, can be optimized later with session checks)
    session_key = f'viewed_post_{post.id}'
    if not request.session.get(session_key, False):
        post.views += 1
        post.save(update_fields=['views'])
        request.session[session_key] = True

    # Related Posts (Same Category)
    related_posts = Post.objects.filter(
        status='published', 
        categories__in=post.categories.all()
    ).exclude(id=post.id).distinct().order_by('-created_at')[:3]
    
    return render(request, 'blog/post_detail.html', {
        'post': post,
        'related_posts': related_posts
    })