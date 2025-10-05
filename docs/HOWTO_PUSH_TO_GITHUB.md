# Как вручную запушить репозиторий в GitHub

Среда, в которой выполняется ассистент, не имеет исходящего сетевого доступа, поэтому он не может выполнить `git push`. Чтобы опубликовать изменения самостоятельно, выполните шаги ниже на своём компьютере или в Codespaces.

## 1. Настройте удалённый репозиторий
```bash
TOKEN="<ВАШ_GITHUB_PAT>"
git remote remove origin 2>/dev/null || true
git remote add origin "https://x-access-token:${TOKEN}@github.com/alexandrivanov-1/LMS.git"
```

## 2. Инициализируйте основную ветку (если репозиторий пуст)
```bash
if ! git ls-remote --exit-code --heads origin main >/dev/null 2>&1; then
  git checkout -B main
  git commit --allow-empty -m "chore: init main"
  git push -u origin main
fi
```

## 3. Опубликуйте фиче-ветку с кодом Stage 1
```bash
git checkout -B feat/stage1-bootstrap
git add -A
git commit -m "feat(bootstrap): Stage 1 scaffold (infra, services, docs, CI)"
git push -u origin feat/stage1-bootstrap
```

## 4. Откройте Pull Request
Создайте PR из ветки `feat/stage1-bootstrap` в `main` со заголовком:
```
feat(bootstrap): Stage 1 scaffold
```
В описании кратко опишите добавленные компоненты: Docker Compose стек, сервисы, CI/CD, демо-страница, Codespaces и интеграционный workflow.

После завершения обязательно удалите токен из `git remote` и переменных окружения:
```bash
git remote set-url origin "https://github.com/alexandrivanov-1/LMS.git"
unset TOKEN
```
