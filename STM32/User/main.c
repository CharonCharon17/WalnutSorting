#include "stm32f10x.h"                  // Device header
#include "Delay.h"
#include "OLED.H"
#include "Serial.H"
#include "Servo.H"
#include "string.h"

uint8_t flage2 = 0;

void Send_up(void)//向上位机发送
{
		static uint8_t lastPinState = 1;
	  uint8_t state0 = GPIO_ReadInputDataBit(GPIOA ,GPIO_Pin_0);//红外传感器，没东西则灭是1，有东西则亮返回0
		if(lastPinState == 1 && state0 == 0)
		{
			Serial_TxPacket[0] = 0x01;
			Serial_SendPacket();
			GPIO_SetBits (GPIOC ,GPIO_Pin_13);
		}
		else if(state0 == 1)
		{
			GPIO_ResetBits (GPIOC ,GPIO_Pin_13);
		}
		lastPinState = state0;
}


//测试
void text()
{
			static uint8_t flage = 1;
			uint8_t state0 = GPIO_ReadInputDataBit(GPIOA ,GPIO_Pin_0);//红外传感器，没东西则灭是1，有东西则亮返回0
			uint8_t state1 = GPIO_ReadInputDataBit(GPIOA ,GPIO_Pin_1);
			uint8_t state2 = GPIO_ReadInputDataBit(GPIOA ,GPIO_Pin_2);

			 if(state1 == 0)
			{
					Servo_SetAngle_R(135);
					Servo_SetAngle_L(45);
			}				
			 if(state0 == 0)
			{
					GPIO_ResetBits(GPIOA,GPIO_Pin_5);//停
					Send_up();
					Delay_ms(50);
					//memset(Serial_RxPacket, 0, 4);//数组清空
					flage = 0;
			}
			 if(flage == 0)
			{
					flage = 1;
					GPIO_SetBits(GPIOA,GPIO_Pin_5);//走
					Servo_SetAngle_R(120);
					Servo_SetAngle_L(60);
			}
			
}


int main(void)
{
	OLED_Init ();
	Serial_Init();	
	Servo_Init();
	GPIO_SetBits(GPIOA,GPIO_Pin_5);
	Servo_SetAngle_R(135);
	Servo_SetAngle_L(45);
	Delay_ms(2000);
	Servo_SetAngle_R(120);
	Servo_SetAngle_L(60);

	while (1)
	{
		text();
		if(Serial_GetRxFlag ()==1)
		{
			if(Serial_RxPacket[0]==0X02 && Serial_RxPacket[1]==0X01)
			{
				flage2 = 1;
				OLED_ShowHexNum(1,1,Serial_RxPacket[0],2);
				OLED_ShowHexNum(2,1,Serial_RxPacket[1],2);
				OLED_ShowHexNum(3,1,Serial_RxPacket[2],2);
				OLED_ShowHexNum(4,1,Serial_RxPacket[3],2);
				OLED_ShowHexNum(3,8,flage2,1);
			}
			if(flage2 == 1)
			{
				GPIO_SetBits(GPIOA,GPIO_Pin_5);//走
				Delay_s(3);
				flage2 = 0;
			}
		}
	}
}
