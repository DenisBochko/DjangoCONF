import requests

from reportlab.pdfbase.ttfonts import TTFont
from django.http import HttpResponse
from reportlab.lib.pagesizes import letter
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfgen import canvas
from io import BytesIO

from django.utils import timezone
from rest_framework.authentication import TokenAuthentication
from rest_framework.exceptions import AuthenticationFailed
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.authtoken.models import Token
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.contrib.auth import authenticate
from django.core.exceptions import ObjectDoesNotExist
from .models import *
from .serializers import MeetingSerializer, AgendaItemSerializer, VoteSerializer
from .serializers import UserSerializer


def check_auth_token(request):
    # Извлекаем токен из заголовка Authorization
    auth_header = request.META.get('HTTP_AUTHORIZATION')

    if not auth_header:
        raise AuthenticationFailed('Authorization header is missing')

    try:
        # Разделяем заголовок на тип и токен (например, "Token <your_token>")
        auth_type, token = auth_header.split()
        if auth_type.lower() != 'token':
            raise AuthenticationFailed('Invalid authorization type')
    except ValueError:
        raise AuthenticationFailed('Invalid authorization header format')

    # Проверяем токен
    try:
        token_obj = Token.objects.get(key=token)
        user = token_obj.user
    except Token.DoesNotExist:
        raise AuthenticationFailed('Invalid token')

    return user


# Регистрация пользователя
class RegisterView(APIView):
    permission_classes = [AllowAny]  # Разрешить доступ всем

    def post(self, request):
        serializer = UserSerializer(data=request.data)
        if serializer.is_valid():
            # Сохраняем нового пользователя
            user = serializer.save()

            # Создаем токен для нового пользователя
            token, created = Token.objects.get_or_create(user=user)

            # Возвращаем токен в ответе
            return Response({
                'token': token.key,
            }, status=status.HTTP_201_CREATED)

        # Если данные невалидны, возвращаем ошибки
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# Авторизация пользователя
class LoginView(APIView):
    permission_classes = [AllowAny]  # Разрешить доступ всем

    def post(self, request):
        email = request.data.get('email')  # Получаем email из запроса
        password = request.data.get('password')

        # Проверяем, что email и пароль предоставлены
        if not email or not password:
            return Response({'error': 'Email and password are required'}, status=400)

        # Находим пользователя по email
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response({'error': 'Invalid credentials'}, status=401)

        # Аутентифицируем пользователя
        user = authenticate(username=user.username, password=password)
        if user is not None:
            # Создаем или получаем токен для пользователя
            token, created = Token.objects.get_or_create(user=user)
            return Response({
                'token': token.key,
            }, status=200)

        # Если авторизация не удалась, возвращаем ошибку
        return Response({'error': 'Invalid credentials'}, status=401)

# TODO сброс пароля


# Профиль
class ProfileView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = check_auth_token(request)

        # Проверяем, существует ли профиль пользователя
        try:
            profile = user.profile
        except AttributeError:
            raise AuthenticationFailed('User profile does not exist')

        return Response({
            'username': user.username,
            'email': user.email,
            'is_admin': profile.is_admin,
            'photo': request.build_absolute_uri(profile.photo.url) if profile.photo else None
        })


class UserUpdateView(APIView):
    """Обновление данных пользователя"""
    permission_classes = [IsAuthenticated]

    def put(self, request):
        user = check_auth_token(request)

        # Используем сериализатор для валидации и обновления данных
        serializer = UserSerializer(user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)

        # Если данные невалидны, возвращаем ошибки
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# Конференции
class MeetingCreateView(APIView):
    """Создание конференции"""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = check_auth_token(request)

        name_room = request.data.get('name_room')
        password_room = request.data.get('password_room')
        date = request.data.get('date')

        # Проверяем, существует ли профиль пользователя
        try:
            profile = user.profile
        except AttributeError:
            raise AuthenticationFailed('User profile does not exist')

        # Проверяем, является ли пользователь администратором
        if not profile.is_admin:
            return Response(
                {"error": "Only admins can create meetings"},
                status=403
            )

        # Генерируем ссылку регистрации
        url = "https://3449009-eq23140.twc1.net/api/create-room"
        headers = {
            "Content-Type": "application/json"
        }
        data = {
            "name": name_room,
            "password": password_room
        }
        response = requests.post(url, headers=headers, json=data)

        # Проверка статуса ответа и вывод данных
        if response.status_code == 200:
            registration_link = response.json()['uri']

            # Создаем новую конференцию
            meeting = Meeting.objects.create(
                registration_link=registration_link,
                name_room=name_room,
                date=date,  # Дата проведения встречи из запроса
                admin=user  # Привязываем создателя к текущему пользователю
            )

            # Возвращаем ссылку на регистрацию
            return Response(
                {
                    "message": "Meeting created successfully",
                    "registration_link": meeting.registration_link
                },
                status=201
            )

        else:
            return Response(
                {
                    "message": "Server error",
                },
                status=500
            )


class MeetingListView(APIView):
    """Список конференций"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = check_auth_token(request)

        # Получаем все встречи, связанные с пользователем
        user_meetings = UserMeetings.objects.filter(user=user).select_related('meeting')

        # Извлекаем связанные объекты Meeting
        meetings = [user_meeting.meeting for user_meeting in user_meetings]

        # Сериализуем встречи
        serializer = MeetingSerializer(meetings, many=True)
        return Response(serializer.data)


class AgendaCreateView(APIView):
    """Создание голосования (вопроса)"""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = check_auth_token(request)

        # Проверяем, существует ли профиль пользователя
        try:
            profile = user.profile
        except AttributeError:
            raise AuthenticationFailed('User profile does not exist')

        # Проверяем, является ли пользователь администратором
        if not profile.is_admin:
            return Response(
                {"error": "Only admins can create meetings"},
                status=403
            )

        # Используем сериализатор для валидации данных
        serializer = AgendaItemSerializer(data=request.data)
        if serializer.is_valid():
            # Сохраняем новый пункт повестки
            serializer.save()
            return Response(
                {
                    "message": "AgendaItem created successfully",
                },
                status=201
            )

        # Если данные невалидны, возвращаем ошибки
        return Response(serializer.errors, status=400)


class AgendasView(APIView):
    """Получить голосования пользователя"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = check_auth_token(request)

        # Получаем все встречи, в которых участвует пользователь
        user_meetings = UserMeetings.objects.filter(user=user)

        # Получаем все agenda_items, связанные с этими встречами
        meeting_ids = user_meetings.values_list('meeting_id', flat=True)
        agenda_items = AgendaItem.objects.filter(meeting_id__in=meeting_ids)

        # Сериализуем данные
        serializer = AgendaItemSerializer(agenda_items, many=True)
        return Response(serializer.data)


class VoteCreateView(APIView):
    """Создание голоса"""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = check_auth_token(request)

        agenda_item_id = request.data.get('agenda_item')

        try:
            agenda_item = AgendaItem.objects.get(pk=agenda_item_id)
        except AgendaItem.DoesNotExist:
            return Response({"error": "Вопрос не найден"}, status=status.HTTP_404_NOT_FOUND)

        # Проверяем, что время голосования открыто
        if not (agenda_item.summary_datetime >= timezone.now()):
            return Response({"error": "Время голосования истекло"}, status=status.HTTP_400_BAD_REQUEST)

        # Проверяем, что пользователь не голосовал ранее
        if Vote.objects.filter(user=request.user, agenda_item=agenda_item).exists():
            return Response({"error": "Вы уже проголосовали"}, status=status.HTTP_400_BAD_REQUEST)

        # Создаем сериализатор и передаем данные
        serializer = VoteSerializer(data=request.data)
        if serializer.is_valid():
            # Сохраняем голос, явно передавая пользователя
            serializer.save(user=user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class VoteUpdateView(APIView):
    """Обновление голоса"""
    permission_classes = [IsAuthenticated]

    def put(self, request):
        user = check_auth_token(request)
        agenda_item_id = request.data.get('agenda_item')

        try:
            agenda_item = AgendaItem.objects.get(pk=agenda_item_id)
        except AgendaItem.DoesNotExist:
            return Response({"error": "Вопрос не найден"}, status=status.HTTP_404_NOT_FOUND)

        try:
            vote = Vote.objects.get(agenda_item=agenda_item, user=user)
        except Vote.DoesNotExist:
            return Response({"error": "Голос не найден"}, status=status.HTTP_404_NOT_FOUND)

        # Проверяем, что время голосования открыто
        if timezone.now() > agenda_item.summary_datetime:
            return Response({"error": "Время голосования истекло"}, status=status.HTTP_400_BAD_REQUEST)

        # Создаем сериализатор и передаем данные
        serializer = VoteSerializer(vote, data=request.data, partial=True)
        if serializer.is_valid():
            # Сохраняем голос, явно передавая пользователя
            serializer.save(user=user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class CheckAuthToken(APIView):
    """Эндпоинт для проверки токена"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        check_auth_token(request)

        return Response({"success": "ok"}, status=status.HTTP_200_OK)


class GenerateProtocolView(APIView):
    """Эндпоинт для генерации PDF-протокола"""
    permission_classes = [AllowAny]

    def get(self, request, agenda_item_id):
        # Получаем пользователя из токена
        user = check_auth_token(request)

        # Проверяем, существует ли профиль пользователя
        try:
            profile = user.profile
        except AttributeError:
            raise AuthenticationFailed('User profile does not exist')

        # Проверяем, что пользователь является администратором
        if not profile.is_admin:
            return Response({"error": "Forbidden"}, status=403)

        # Получаем объект AgendaItem
        try:
            agenda_item = AgendaItem.objects.get(id=agenda_item_id)
        except AgendaItem.DoesNotExist:
            return Response({"error": "Agenda item not found"}, status=404)

        # Получаем голоса по этому вопросу
        votes = Vote.objects.filter(agenda_item=agenda_item)

        # Регистрация шрифта DejaVuSans для поддержки кириллицы
        pdfmetrics.registerFont(TTFont('DejaVuSans', 'DejaVuSans.ttf'))

        # Генерируем PDF
        buffer = BytesIO()
        p = canvas.Canvas(buffer, pagesize=letter)

        # Устанавливаем шрифт с поддержкой кириллицы
        p.setFont("DejaVuSans", 14)

        # Заголовок протокола
        p.drawString(50, 750, f"ПРОТОКОЛ № {agenda_item.id}")
        p.drawString(50, 730, "заочного голосования Совета директоров")
        p.drawString(50, 710, "ПАО «ТНС энерго Ростов-на-Дону»")

        # Дата и время окончания приема документов
        summary_datetime = agenda_item.summary_datetime.strftime("%d %B %Y года, %H:%M")
        p.setFont("DejaVuSans", 12)
        p.drawString(50, 680, f"Дата и время окончания приема документов: {summary_datetime} по московскому времени.")
        p.drawString(50, 660, f"Место подведения итогов заочного голосования: Москва")
        p.drawString(50, 640, f"Форма проведения: {agenda_item.get_meeting_type_display()}.")

        # Дата составления протокола
        protocol_date = agenda_item.summary_datetime.strftime("%d %B %Y года")
        p.drawString(50, 620, f"Дата составления протокола: {protocol_date}.")

        # Лица, принявшие участие в голосовании
        participants = ", ".join([vote.user.username for vote in votes])
        p.drawString(50, 600, f"Лица, принявшие участие в заочном голосовании: {participants}.")
        p.drawString(50, 580, f"Лицо, проводившее подсчет голосов: {user.username}.")

        # Кворум
        p.drawString(50, 560,
                     "Кворум для подведения итогов заочного голосования Совета директоров с данной повесткой дня имеется.")

        # Повестка дня
        p.setFont("DejaVuSans-Bold", 12)
        p.drawString(50, 530, "ПОВЕСТКА ДНЯ:")
        p.setFont("DejaVuSans", 12)
        p.drawString(50, 510, f"ВОПРОС № 1:")
        p.drawString(50, 490, f"Вопрос повестки дня, поставленный на голосование:")
        p.drawString(50, 470, f"{agenda_item.title}")
        p.drawString(50, 450, f"Проект решения, поставленный на голосование:")
        p.drawString(50, 430, f"{agenda_item.description}")

        # Результаты голосования
        yes_votes = votes.filter(vote="yes").count()
        no_votes = votes.filter(vote="no").count()
        abstain_votes = votes.filter(vote="abstain").count()

        p.drawString(50, 410, "Результаты (итоги) голосования:")
        p.drawString(50, 390, f"ЗА – {yes_votes} голосов.")
        p.drawString(50, 370, f"ПРОТИВ – {no_votes} голосов.")
        p.drawString(50, 350, f"ВОЗДЕРЖАЛИСЬ – {abstain_votes} голосов.")

        # Итоговое решение
        decision = "Решение принято." if yes_votes > no_votes else "Решение не принято."
        p.drawString(50, 330, decision)

        # Завершение документа
        p.showPage()
        p.save()

        print(2)

        # Получаем содержимое PDF
        buffer.seek(0)
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="protocol_{agenda_item.id}.pdf"'
        response.write(buffer.getvalue())
        buffer.close()

        return response