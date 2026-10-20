from __future__ import annotations

from .config import Settings
from .ledger import Ledger
from .models import ProviderResponse, Task
from .providers import ProviderError, providers


class ControlTower:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.ledger = Ledger(settings.db_path)
        self.providers = providers()

    def run(self, prompt: str, provider_name: str | None = None,
            system: str | None = None) -> ProviderResponse:
        name = (provider_name or self.settings.default_provider).lower()
        if name not in self.providers:
            raise ProviderError(f"Unknown provider '{name}'. Choose: {', '.join(self.providers)}")
        task = Task(prompt=prompt, provider=name, **({"system": system} if system else {}))
        self.ledger.create_task(task)
        try:
            response = self.providers[name].complete(task, self.settings.timeout_seconds)
            self.ledger.complete_task(response)
            return response
        except Exception as exc:
            self.ledger.fail_task(task.id, exc)
            raise

    def health(self) -> dict[str, object]:
        return {"status": "ok", "database": str(self.settings.db_path),
                "default_provider": self.settings.default_provider,
                "providers": {name: {"configured": provider.configured()}
                              for name, provider in self.providers.items()}}
