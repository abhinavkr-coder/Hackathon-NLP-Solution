---
tags:
- sentence-transformers
- sentence-similarity
- feature-extraction
- dense
- generated_from_trainer
- dataset_size:80
- loss:CosineSimilarityLoss
base_model: sentence-transformers/all-MiniLM-L6-v2
widget:
- source_sentence: The Count of Monte Cristo - Faria
  sentences:
  - Born in Parma to a theological family—his father studied ancient manuscripts,
    his mother wrote poetry in several tongues.
  - He declined to take part in charting the maiden voyage of the Britannia; when
    news of her wreck arrived he filled three diary pages with the sentence “I could
    have prevented it.”
  - '**Father-son Rift**: Discovering that his elder son Gérard (Villefort) sought
    to wed into the old aristocracy, Noirtier publicly burned the Saint-Méran betrothal
    contract (1804), forcing Villefort to flee to Paris overnight.'
- source_sentence: In Search of the Castaways - Thalcave
  sentences:
  - After discharge he adopted the alias Ben Joyce and shipped on the Liverpool–Lisbon
    trader, forming a mentor-friend bond with Captain Dewey and second mate Eddie.
  - British officers marvelled that he handled canoe, coast and jungle with equal
    ease, shuttling supplies and so preparing his later berth on the Dartmouth.
  - He briefly loved Chilean doctor Mariana, who wanted him to settle down but was
    refused; she died nursing cholera-stricken Indians. When he burned her belongings
    he kept the brass compass she had given him.
- source_sentence: In Search of the Castaways - Kai-Koumou
  sentences:
  - Born on New Zealand’s North-island east coast to a Maori war-chief father and
    a priestess mother skilled in herbs and star-reading, he saw his father ambushed
    by a British musket squad, the body mutilated, the left ear taken as trophy; his
    mother tattooed a vengeance curse on his chest with ochre.
  - Finding missionaries wrapping opium in Bible pages, he ordered every book burned
    except the sheepskin map showing ancestral migration routes.
  - Thalcave’s people faded as colonists advanced; his father, last of the tribal
    guides, knew the pampas geography and animal ways, while his mother died giving
    birth. Boyhood was spent roaming the plains with his father, learning to track,
    tame horses and steer by the stars.
- source_sentence: In Search of the Castaways - Jacques Paganel
  sentences:
  - After his mother died she entrusted him with the care of his toddler half-brother;
    the child was later taken to Europe by the French stepfather and never heard from
    again, leaving Paganel with a lifelong dread of “separation by life and death.”
  - He saved an old shepherd bitten by a viper; in gratitude the man gave him a secret
    map of pampas water-holes and taught him that a guide’s duty is to keep life moving.
  - Suspected of colluding with the enemy, he panicked, slipped away in a lifeboat
    under darkness and fled to the Southern Hemisphere.
- source_sentence: In Search of the Castaways - Tom Ayrton/Ben Joyce
  sentences:
  - '**Turning Point**: Arguing for procedural justice at Louis XVI’s trial (1793)
    he was driven from the inner circle, an experience that later anchored his insistence
    on legal formalism.'
  - With the rescue squad he learned enough nautical English to converse with Captain
    Horace and the sailors.
  - He found ship’s papers that mentioned an illicit Australian land deal by a British
    peer and planned to trade the information for a pardon.
pipeline_tag: sentence-similarity
library_name: sentence-transformers
---

# SentenceTransformer based on sentence-transformers/all-MiniLM-L6-v2

This is a [sentence-transformers](https://www.SBERT.net) model finetuned from [sentence-transformers/all-MiniLM-L6-v2](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2). It maps sentences & paragraphs to a 384-dimensional dense vector space and can be used for semantic textual similarity, semantic search, paraphrase mining, text classification, clustering, and more.

## Model Details

### Model Description
- **Model Type:** Sentence Transformer
- **Base model:** [sentence-transformers/all-MiniLM-L6-v2](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2) <!-- at revision c9745ed1d9f207416be6d2e6f8de32d1f16199bf -->
- **Maximum Sequence Length:** 256 tokens
- **Output Dimensionality:** 384 dimensions
- **Similarity Function:** Cosine Similarity
<!-- - **Training Dataset:** Unknown -->
<!-- - **Language:** Unknown -->
<!-- - **License:** Unknown -->

### Model Sources

- **Documentation:** [Sentence Transformers Documentation](https://sbert.net)
- **Repository:** [Sentence Transformers on GitHub](https://github.com/huggingface/sentence-transformers)
- **Hugging Face:** [Sentence Transformers on Hugging Face](https://huggingface.co/models?library=sentence-transformers)

### Full Model Architecture

```
SentenceTransformer(
  (0): Transformer({'max_seq_length': 256, 'do_lower_case': False, 'architecture': 'BertModel'})
  (1): Pooling({'word_embedding_dimension': 384, 'pooling_mode_cls_token': False, 'pooling_mode_mean_tokens': True, 'pooling_mode_max_tokens': False, 'pooling_mode_mean_sqrt_len_tokens': False, 'pooling_mode_weightedmean_tokens': False, 'pooling_mode_lasttoken': False, 'include_prompt': True})
  (2): Normalize()
)
```

## Usage

### Direct Usage (Sentence Transformers)

First install the Sentence Transformers library:

```bash
pip install -U sentence-transformers
```

Then you can load this model and run inference.
```python
from sentence_transformers import SentenceTransformer

# Download from the 🤗 Hub
model = SentenceTransformer("sentence_transformers_model_id")
# Run inference
sentences = [
    'In Search of the Castaways - Tom Ayrton/Ben Joyce',
    'He found ship’s papers that mentioned an illicit Australian land deal by a British peer and planned to trade the information for a pardon.',
    'With the rescue squad he learned enough nautical English to converse with Captain Horace and the sailors.',
]
embeddings = model.encode(sentences)
print(embeddings.shape)
# [3, 384]

# Get the similarity scores for the embeddings
similarities = model.similarity(embeddings, embeddings)
print(similarities)
# tensor([[1.0000, 0.3004, 0.2708],
#         [0.3004, 1.0000, 0.3557],
#         [0.2708, 0.3557, 1.0000]])
```

<!--
### Direct Usage (Transformers)

<details><summary>Click to see the direct usage in Transformers</summary>

</details>
-->

<!--
### Downstream Usage (Sentence Transformers)

You can finetune this model on your own dataset.

<details><summary>Click to expand</summary>

</details>
-->

<!--
### Out-of-Scope Use

*List how the model may foreseeably be misused and address what users ought not to do with the model.*
-->

<!--
## Bias, Risks and Limitations

*What are the known or foreseeable issues stemming from this model? You could also flag here known failure cases or weaknesses of the model.*
-->

<!--
### Recommendations

*What are recommendations with respect to the foreseeable issues? For example, filtering explicit content.*
-->

## Training Details

### Training Dataset

#### Unnamed Dataset

* Size: 80 training samples
* Columns: <code>sentence_0</code>, <code>sentence_1</code>, and <code>label</code>
* Approximate statistics based on the first 80 samples:
  |         | sentence_0                                                                         | sentence_1                                                                         | label                                                          |
  |:--------|:-----------------------------------------------------------------------------------|:-----------------------------------------------------------------------------------|:---------------------------------------------------------------|
  | type    | string                                                                             | string                                                                             | float                                                          |
  | details | <ul><li>min: 11 tokens</li><li>mean: 13.07 tokens</li><li>max: 17 tokens</li></ul> | <ul><li>min: 20 tokens</li><li>mean: 36.73 tokens</li><li>max: 89 tokens</li></ul> | <ul><li>min: 0.0</li><li>mean: 0.64</li><li>max: 1.0</li></ul> |
* Samples:
  | sentence_0                                         | sentence_1                                                                                                                                                                                                                                                                                     | label            |
  |:---------------------------------------------------|:-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|:-----------------|
  | <code>In Search of the Castaways - Thalcave</code> | <code>Thalcave’s people faded as colonists advanced; his father, last of the tribal guides, knew the pampas geography and animal ways, while his mother died giving birth. Boyhood was spent roaming the plains with his father, learning to track, tame horses and steer by the stars.</code> | <code>1.0</code> |
  | <code>In Search of the Castaways - Thalcave</code> | <code>He briefly loved Chilean doctor Mariana, who wanted him to settle down but was refused; she died nursing cholera-stricken Indians. When he burned her belongings he kept the brass compass she had given him.</code>                                                                     | <code>1.0</code> |
  | <code>The Count of Monte Cristo - Noirtier</code>  | <code>**Father-son Rift**: Discovering that his elder son Gérard (Villefort) sought to wed into the old aristocracy, Noirtier publicly burned the Saint-Méran betrothal contract (1804), forcing Villefort to flee to Paris overnight.</code>                                                  | <code>0.0</code> |
* Loss: [<code>CosineSimilarityLoss</code>](https://sbert.net/docs/package_reference/sentence_transformer/losses.html#cosinesimilarityloss) with these parameters:
  ```json
  {
      "loss_fct": "torch.nn.modules.loss.MSELoss"
  }
  ```

### Training Hyperparameters
#### Non-Default Hyperparameters

- `per_device_train_batch_size`: 16
- `per_device_eval_batch_size`: 16
- `multi_dataset_batch_sampler`: round_robin

#### All Hyperparameters
<details><summary>Click to expand</summary>

- `overwrite_output_dir`: False
- `do_predict`: False
- `eval_strategy`: no
- `prediction_loss_only`: True
- `per_device_train_batch_size`: 16
- `per_device_eval_batch_size`: 16
- `per_gpu_train_batch_size`: None
- `per_gpu_eval_batch_size`: None
- `gradient_accumulation_steps`: 1
- `eval_accumulation_steps`: None
- `torch_empty_cache_steps`: None
- `learning_rate`: 5e-05
- `weight_decay`: 0.0
- `adam_beta1`: 0.9
- `adam_beta2`: 0.999
- `adam_epsilon`: 1e-08
- `max_grad_norm`: 1
- `num_train_epochs`: 3
- `max_steps`: -1
- `lr_scheduler_type`: linear
- `lr_scheduler_kwargs`: {}
- `warmup_ratio`: 0.0
- `warmup_steps`: 0
- `log_level`: passive
- `log_level_replica`: warning
- `log_on_each_node`: True
- `logging_nan_inf_filter`: True
- `save_safetensors`: True
- `save_on_each_node`: False
- `save_only_model`: False
- `restore_callback_states_from_checkpoint`: False
- `no_cuda`: False
- `use_cpu`: False
- `use_mps_device`: False
- `seed`: 42
- `data_seed`: None
- `jit_mode_eval`: False
- `bf16`: False
- `fp16`: False
- `fp16_opt_level`: O1
- `half_precision_backend`: auto
- `bf16_full_eval`: False
- `fp16_full_eval`: False
- `tf32`: None
- `local_rank`: 0
- `ddp_backend`: None
- `tpu_num_cores`: None
- `tpu_metrics_debug`: False
- `debug`: []
- `dataloader_drop_last`: False
- `dataloader_num_workers`: 0
- `dataloader_prefetch_factor`: None
- `past_index`: -1
- `disable_tqdm`: False
- `remove_unused_columns`: True
- `label_names`: None
- `load_best_model_at_end`: False
- `ignore_data_skip`: False
- `fsdp`: []
- `fsdp_min_num_params`: 0
- `fsdp_config`: {'min_num_params': 0, 'xla': False, 'xla_fsdp_v2': False, 'xla_fsdp_grad_ckpt': False}
- `fsdp_transformer_layer_cls_to_wrap`: None
- `accelerator_config`: {'split_batches': False, 'dispatch_batches': None, 'even_batches': True, 'use_seedable_sampler': True, 'non_blocking': False, 'gradient_accumulation_kwargs': None}
- `parallelism_config`: None
- `deepspeed`: None
- `label_smoothing_factor`: 0.0
- `optim`: adamw_torch_fused
- `optim_args`: None
- `adafactor`: False
- `group_by_length`: False
- `length_column_name`: length
- `project`: huggingface
- `trackio_space_id`: trackio
- `ddp_find_unused_parameters`: None
- `ddp_bucket_cap_mb`: None
- `ddp_broadcast_buffers`: False
- `dataloader_pin_memory`: True
- `dataloader_persistent_workers`: False
- `skip_memory_metrics`: True
- `use_legacy_prediction_loop`: False
- `push_to_hub`: False
- `resume_from_checkpoint`: None
- `hub_model_id`: None
- `hub_strategy`: every_save
- `hub_private_repo`: None
- `hub_always_push`: False
- `hub_revision`: None
- `gradient_checkpointing`: False
- `gradient_checkpointing_kwargs`: None
- `include_inputs_for_metrics`: False
- `include_for_metrics`: []
- `eval_do_concat_batches`: True
- `fp16_backend`: auto
- `push_to_hub_model_id`: None
- `push_to_hub_organization`: None
- `mp_parameters`: 
- `auto_find_batch_size`: False
- `full_determinism`: False
- `torchdynamo`: None
- `ray_scope`: last
- `ddp_timeout`: 1800
- `torch_compile`: False
- `torch_compile_backend`: None
- `torch_compile_mode`: None
- `include_tokens_per_second`: False
- `include_num_input_tokens_seen`: no
- `neftune_noise_alpha`: None
- `optim_target_modules`: None
- `batch_eval_metrics`: False
- `eval_on_start`: False
- `use_liger_kernel`: False
- `liger_kernel_config`: None
- `eval_use_gather_object`: False
- `average_tokens_across_devices`: True
- `prompts`: None
- `batch_sampler`: batch_sampler
- `multi_dataset_batch_sampler`: round_robin
- `router_mapping`: {}
- `learning_rate_mapping`: {}

</details>

### Framework Versions
- Python: 3.13.4
- Sentence Transformers: 5.2.0
- Transformers: 4.57.3
- PyTorch: 2.9.1+cpu
- Accelerate: 1.12.0
- Datasets: 4.4.2
- Tokenizers: 0.22.2

## Citation

### BibTeX

#### Sentence Transformers
```bibtex
@inproceedings{reimers-2019-sentence-bert,
    title = "Sentence-BERT: Sentence Embeddings using Siamese BERT-Networks",
    author = "Reimers, Nils and Gurevych, Iryna",
    booktitle = "Proceedings of the 2019 Conference on Empirical Methods in Natural Language Processing",
    month = "11",
    year = "2019",
    publisher = "Association for Computational Linguistics",
    url = "https://arxiv.org/abs/1908.10084",
}
```

<!--
## Glossary

*Clearly define terms in order to be accessible across audiences.*
-->

<!--
## Model Card Authors

*Lists the people who create the model card, providing recognition and accountability for the detailed work that goes into its construction.*
-->

<!--
## Model Card Contact

*Provides a way for people who have updates to the Model Card, suggestions, or questions, to contact the Model Card authors.*
-->