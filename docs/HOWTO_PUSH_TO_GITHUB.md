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

## 3. Обновите ветку Stage 1 относительно main
```bash
git fetch origin
git checkout feat/stage1-bootstrap
git rebase origin/main
# при необходимости объедините коммиты Stage 1 в один: git rebase -i origin/main
git push -f origin feat/stage1-bootstrap
```

## 4. Откройте Pull Request и выполните squash-merge в main
1. Создайте PR `feat/stage1-bootstrap` → `main` с заголовком `feat(bootstrap): Stage 1 scaffold`.
2. Дождитесь прохождения workflows `CI` и `Integration` в GitHub Actions.
3. Выполните **Squash & Merge** в веб-интерфейсе GitHub.
4. Удалите ветку `feat/stage1-bootstrap` в веб-интерфейсе или командой:
   ```bash
   git push origin --delete feat/stage1-bootstrap
   ```

## 5. Зафиксируйте релиз в main
```bash
git checkout main
git pull --ff-only origin main
git tag v0.1.0-stage1-bootstrap
git push origin v0.1.0-stage1-bootstrap
```

После завершения обязательно удалите токен из `git remote` и переменных окружения:
```bash
git remote set-url origin "https://github.com/alexandrivanov-1/LMS.git"
unset TOKEN
```
