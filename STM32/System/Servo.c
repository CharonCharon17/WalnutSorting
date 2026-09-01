#include "stm32f10x.h"                  // Device header


void Servo_Init(void)
{
	RCC_APB1PeriphClockCmd (RCC_APB1Periph_TIM3  ,ENABLE );
	RCC_APB2PeriphClockCmd(RCC_APB2Periph_GPIOA, ENABLE);
	
	GPIO_InitTypeDef GPIO_InitStructure;
	GPIO_InitStructure.GPIO_Mode = GPIO_Mode_AF_PP;
	GPIO_InitStructure.GPIO_Pin = GPIO_Pin_6 | GPIO_Pin_7 ;
	GPIO_InitStructure.GPIO_Speed = GPIO_Speed_50MHz;
	GPIO_Init (GPIOA,&GPIO_InitStructure);

	//红外对射初始化
	GPIO_InitTypeDef GPIO_InitStructureIO;
	GPIO_InitStructureIO.GPIO_Mode =GPIO_Mode_IPU;
	GPIO_InitStructureIO.GPIO_Pin = GPIO_Pin_0 | GPIO_Pin_1 | GPIO_Pin_2;
	GPIO_InitStructureIO.GPIO_Speed =GPIO_Speed_50MHz ;
	GPIO_Init (GPIOA,&GPIO_InitStructureIO);

	//继电器初始化
	GPIO_InitTypeDef GPIO_InitStructur;
	GPIO_InitStructur.GPIO_Mode =GPIO_Mode_Out_PP;
	GPIO_InitStructur.GPIO_Pin = GPIO_Pin_5;
	GPIO_InitStructur.GPIO_Speed =GPIO_Speed_50MHz ;
	GPIO_Init (GPIOA,&GPIO_InitStructur);
	
	TIM_InternalClockConfig(TIM3);
	
	TIM_TimeBaseInitTypeDef TIM_TimeBsaeInitStructure;
	TIM_TimeBsaeInitStructure.TIM_ClockDivision =TIM_CKD_DIV1;
	TIM_TimeBsaeInitStructure.TIM_CounterMode =TIM_CounterMode_Up;
	TIM_TimeBsaeInitStructure.TIM_Period =20000-1;      //ARR
	TIM_TimeBsaeInitStructure.TIM_Prescaler =72-1;    //PSC
	TIM_TimeBsaeInitStructure.TIM_RepetitionCounter =0;
	TIM_TimeBaseInit (TIM3 ,&TIM_TimeBsaeInitStructure);
	
	
	TIM_OCInitTypeDef TIM_OCInitStructure;
	TIM_OCStructInit(&TIM_OCInitStructure);//给结构体成员赋初始值，里面给结构体全部复制，要更改直接下面更改
	
	TIM_OCInitStructure.TIM_OCMode =TIM_OCMode_PWM1;
	TIM_OCInitStructure.TIM_OCPolarity =TIM_OCPolarity_High;
	TIM_OCInitStructure.TIM_OutputState =TIM_OutputState_Enable;
	TIM_OCInitStructure.TIM_Pulse =0;//CCR的值
	
	TIM_OC2Init(TIM3,&TIM_OCInitStructure);
	TIM_OC1Init(TIM3,&TIM_OCInitStructure);
	
	TIM_Cmd(TIM3 ,ENABLE);
}


void PWM_SetCompare1(uint16_t Compare)
{
    TIM_SetCompare1(TIM3, Compare);  
}

void PWM_SetCompare2(uint16_t Compare)
{
    TIM_SetCompare2(TIM3, Compare);  
}

void Servo_SetAngle_R(float Angle)
{
	PWM_SetCompare1(Angle / 180 * 2000 + 500);
}

void Servo_SetAngle_L(float Angle)
{
	PWM_SetCompare2(Angle / 180 * 2000 + 500);
}

