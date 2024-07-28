# sentiment analysis
#accelerate launch train_lora.py \
 #--run_name sentiment-phi3medium-linear-1e-4lr \
 #--base_model phi3medium \
 #--dataset fiqa,fpb,nwgi,tfns,sentiment-cls \
 #--test_dataset fiqa,fpb,nwgi,tfns,sentiment-cls \
 #--max_length 512 \
 #--batch_size 4 \
 #--learning_rate 1e-4 \
 #--num_epochs 1 \
 #--gradient_steps 1 \
 #--log_interval 10 \
 #--warmup_ratio 0.03 \
 #--scheduler linear \
 #--evaluation_strategy steps \

# multi-task learning
accelerate launch train_lora.py \
 --run_name mt-phi3mini-linear-1e-4lr \
 --base_model phi3mini \
 --dataset fiqa,fpb,nwgi,tfns,sentiment-cls,finred,fiqa_qa,convfinqa,headline-cls,headline-instruct,ner,ner-cls \
 --test_dataset fiqa,fpb,nwgi,tfns,sentiment-cls \
 --max_length 512 \
 --batch_size 4 \
 --learning_rate 1e-4 \
 --num_epochs 1 \
 --gradient_steps 1 \
 --log_interval 10 \
 --warmup_ratio 0.03 \
 --scheduler linear \
 --evaluation_strategy steps \
