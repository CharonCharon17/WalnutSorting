#ifndef  __Serial_H__
#define  __Serial_H__

extern uint8_t Serial_TxPacket[4];
extern uint8_t Serial_RxPacket[4];

void Serial_Init(void);
void Serial_SendByte(uint8_t Byte);
void Serial_SendArray(uint8_t *Array, uint16_t Length);
void Serial_SendPacket(void);
uint8_t Serial_GetRxFlag(void);

void USART1_IRQHandler(void);

#endif
