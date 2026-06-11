"""MediaPlatform protocol — the contract every platform implementation satisfies."""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class MediaPlatform(Protocol):
    """Platform-agnostic interface for the enumerate → group → select → download pipeline.

    Each platform provides its own item dataclass and implements all four stages.
    The pipeline operates on ``list[Any]`` so the protocol stays generic; concrete
    types are enforced within each platform module.
    """

    def enumerate(self) -> list[Any]:
        """Walk the source, collect metadata, cache results as JSON.

        Returns
        -------
        list[Any]
            Platform-specific item objects (dataclasses or dicts).
        """
        ...

    def group(self, items: list[Any]) -> dict[str, list[Any]]:
        """Organise items for browsing (e.g. by year, by playlist).

        Parameters
        ----------
        items:
            The full list returned by :meth:`enumerate`.

        Returns
        -------
        dict[str, list[Any]]
            Ordered mapping of group label → items in that group.
        """
        ...

    def select(self, grouped_items: dict[str, list[Any]]) -> list[Any]:
        """Present an interactive CLI selector; return items chosen for download.

        Parameters
        ----------
        grouped_items:
            The mapping returned by :meth:`group`.

        Returns
        -------
        list[Any]
            The subset of items the user has chosen to download.
        """
        ...

    def download(self, queue: list[Any]) -> None:
        """Fetch selected items to local storage with rate-limiting.

        Parameters
        ----------
        queue:
            Items returned by :meth:`select`.
        """
        ...
