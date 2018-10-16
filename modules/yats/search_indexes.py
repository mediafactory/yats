# -*- coding: utf-8 -*-
from haystack import indexes
from models import docs
from shortcuts import get_ticket_model


class DocIndex(indexes.SearchIndex, indexes.Indexable):
    text = indexes.CharField(document=True, use_template=True)
    caption = indexes.CharField(model_attr='caption')

    def prepare_caption(self, obj):
        return obj.caption[:245]

    def get_model(self):
        return docs

    def get_updated_field(self):
        return 'u_date'

    def index_queryset(self, using=None):
        """Used when the entire index for model is updated."""
        return self.get_model().objects.filter(active_record=True)


class TicketIndex(indexes.SearchIndex, indexes.Indexable):
    text = indexes.CharField(document=True, use_template=True, template_name='search/indexes/yats/ticket_text.txt')
    caption = indexes.CharField(model_attr='caption')
    closed = indexes.BooleanField(model_attr='closed')

    def prepare_caption(self, obj):
        return obj.caption[:245]

    def get_model(self):
        return get_ticket_model()

    def get_updated_field(self):
        return 'last_action_date'

    def index_queryset(self, using=None):
        """Used when the entire index for model is updated."""
        return self.get_model().objects.filter(active_record=True)
