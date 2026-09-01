#include "stm32f10x.h"                  // Device header

uint8_t Serial_TxPacket[4];				//FF 01 02 03 04 FE
uint8_t Serial_RxPacket[4];				
uint8_t Serial_RxFlag;				

void Serial_Init(void)
{
	RCC_APB2PeriphClockCmd (RCC_APB2Periph_USART1 | RCC_APB2Periph_GPIOA | RCC_APB2Periph_GPIOC,ENABLE );
	
	//TX
	GPIO_InitTypeDef GPIO_StructInit;
	GPIO_StructInit.GPIO_Mode =GPIO_Mode_AF_PP;
	GPIO_StructInit.GPIO_Pin =GPIO_Pin_9 ;
	GPIO_StructInit.GPIO_Speed =GPIO_Speed_50MHz ;
	GPIO_Init (GPIOA,&GPIO_StructInit);
	//RX
	GPIO_StructInit.GPIO_Mode =GPIO_Mode_IPU;
	GPIO_StructInit.GPIO_Pin =GPIO_Pin_10;
	GPIO_StructInit.GPIO_Speed =GPIO_Speed_50MHz ;
	GPIO_Init (GPIOA,&GPIO_StructInit);
	
	GPIO_StructInit.GPIO_Mode =GPIO_Mode_Out_PP;
	GPIO_StructInit.GPIO_Pin =GPIO_Pin_13;
	GPIO_StructInit.GPIO_Speed =GPIO_Speed_50MHz ;
	
	GPIO_Init (GPIOC,&GPIO_StructInit);
	


	
	USART_InitTypeDef USART_InitStruct;
	USART_InitStruct.USART_BaudRate =9600;
	USART_InitStruct.USART_HardwareFlowControl = USART_HardwareFlowControl_None;
	USART_InitStruct.USART_Mode = USART_Mode_Rx | USART_Mode_Tx ;
	USART_InitStruct.USART_Parity =USART_Parity_No;
	USART_InitStruct.USART_StopBits =USART_StopBits_1 ;
	USART_InitStruct.USART_WordLength =USART_WordLength_8b ;

	USART_Init (USART1,&USART_InitStruct);
	
	USART_ITConfig(USART1,USART_IT_RXNE,ENABLE);
	
	NVIC_PriorityGroupConfig(NVIC_PriorityGroup_2);
		
	NVIC_InitTypeDef NVIC_InitStructure;
	NVIC_InitStructure.NVIC_IRQChannel =USART1_IRQn;
	NVIC_InitStructure.NVIC_IRQChannelCmd =ENABLE ;
	NVIC_InitStructure.NVIC_IRQChannelPreemptionPriority =1;
	NVIC_InitStructure.NVIC_IRQChannelSubPriority =0;
		
	NVIC_Init(&NVIC_InitStructure);

	
	USART_Cmd (USART1,ENABLE);

}

void Serial_SendByte(uint8_t Byte)
{
	USART_SendData(USART1, Byte);		
	while (USART_GetFlagStatus(USART1, USART_FLAG_TXE) == RESET);	
}

void Serial_SendArray(uint8_t *Array, uint16_t Length)
{
	uint16_t i;
	for (i = 0; i < Length; i ++)	
	{
		Serial_SendByte(Array[i]);		
	}
}

void Serial_SendPacket(void)
{
	Serial_SendByte(0xFF);
	Serial_SendArray(Serial_TxPacket, 4);
	Serial_SendByte(0xFE);
}

uint8_t Serial_GetRxFlag(void)
{
	if (Serial_RxFlag == 1)			
	{
		Serial_RxFlag = 0;
		return 1;					
	}
	return 0;						
}

void USART1_IRQHandler(void)
{
	
	static uint8_t RxState = 0;		
	static uint8_t pRxPacket = 0;
	
	if(USART_GetITStatus(USART1 ,USART_IT_RXNE )==SET )
	{
		uint8_t RxData = USART_ReceiveData(USART1);	
		if (RxState == 0)
		{
			if (RxData == 0xFF)			
			{
				RxState = 1;			
				pRxPacket = 0;		
			}
		}
		else if (RxState == 1)
		{
			Serial_RxPacket[pRxPacket] = RxData;	
			pRxPacket ++;				
			if (pRxPacket >= 4)			
			{
				RxState = 2;			
			}
		}

		else if (RxState == 2)
		{
			if (RxData == 0xFE)			
			{
				RxState = 0;			
				Serial_RxFlag = 1;		
			}
		}
		USART_ClearITPendingBit (USART1 ,USART_IT_RXNE);//清楚标志位
	}
}
