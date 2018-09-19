# -*- coding: utf-8 -*-
from haystack import indexes
from models import docs
from shortcuts import get_ticket_model


class DocIndex(indexes.SearchIndex, indexes.Indexable):
    text = indexes.CharField(document=True, use_template=True)
    caption = indexes.CharField(model_attr='caption')

    def get_model(self):
        return docs

    def index_queryset(self, using=None):
        """Used when the entire index for model is updated."""
        return self.get_model().objects.filter(active_record=True)


class TicketIndex(indexes.SearchIndex, indexes.Indexable):
    text = indexes.CharField(document=True, use_template=True, template_name='search/indexes/yats/ticket_text.txt')
    caption = indexes.CharField(model_attr='caption')

    def get_model(self):
        return get_ticket_model()

    def index_queryset(self, using=None):
        """Used when the entire index for model is updated."""
        return self.get_model().objects.filter(active_record=True)
