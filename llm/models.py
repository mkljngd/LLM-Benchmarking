from django.db import models


# Used to store all the questions
class Question(models.Model):
    question = models.CharField(max_length=500)


# Used to store details about each LLM model
class Model(models.Model):
    model_name = models.CharField(max_length=255)
    model_value = models.CharField(max_length=255, null=True, blank=True)
    parameters = models.CharField(max_length=255, null=True, blank=True)


# Used to store response detail for all unique pairs of LLM model and question
class Response(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    model = models.ForeignKey(Model, on_delete=models.CASCADE)
    execution_time = models.FloatField(null=True, blank=True, default=None)
    energy_usage = models.FloatField(null=True, blank=True, default=None)
    memory_usage = models.FloatField(null=True, blank=True, default=None)
