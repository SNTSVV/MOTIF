/*
Code automatically generated by asn1scc tool
*/
#include <limits.h>
#include <string.h>
#include <math.h>

#include "asn1crt_encoding.h"
#include "asn1crt_encoding_uper.h"

#include "test.h"

const MyInt myVar = 4;
const ConfigString myStrVar = "This is a test";
const FixedLenConfigString myStrFixed = "Hello";
const T_TypeThatMustNotBeMappedExceptInPython push_it = {
    .config = "Config",
    .param = 5,
    .fixstr = "World",
    .exist = {
        .fixstr = 1
    }
};



void TypeWithOptional_Initialize(
        int ca, void * vo,
        const int* a, const float b[3], float c[], char d[],
        const __uint32_t k,
        const asn1SccSint tim,
        const T_SET_data3* fo1,
        const FixedLenConfigString name,
        const T_TypeThatMustNotBeMappedExceptInPython* test,
        const TypeWithOptional* pVal)
{
	(void)pVal;
	(void)name;



	/*set a */
	pVal->exist.a = 1;
	pVal->a = FALSE;
	/*set b */
	TypeWithOptional_b_Initialize((&(pVal->b)));
	/*set c */
	TypeWithOptional_c_Initialize((&(pVal->c)));
	/*set d */
	pVal->exist.d = 1;
	strcpy(pVal->d.config,"Config");
	pVal->d.param = 5;
	pVal->d.exist.fixstr = 1;
	strcpy(pVal->d.fixstr,"World");
}

flag TypeWithOptional_IsConstraintValid(const TypeWithOptional* pVal, int* pErrCode)
{
    flag ret = TRUE;
	(void)pVal;
	
    ret = (((pVal->b <= 255UL)) || ((pVal->b == 1299UL)));
    *pErrCode = ret ? 0 :  ERR_TYPEWITHOPTIONAL_B; 
    if (ret) {
        ret = (pVal->c <= 255UL);
        *pErrCode = ret ? 0 :  ERR_TYPEWITHOPTIONAL_C; 
        if (ret) {
            if (pVal->exist.d) {
            	ret = T_TypeThatMustNotBeMappedExceptInPython_IsConstraintValid((&(pVal->d)), pErrCode);
            }
        }
    }

	return ret;
}

flag TypeWithOptional_Encode(const TypeWithOptional* pVal, BitStream* pBitStrm, int* pErrCode, flag bCheckConstraints)
{
    flag ret = TRUE;
	(void)pVal;
	(void)pBitStrm;


	ret = bCheckConstraints ? TypeWithOptional_IsConstraintValid(pVal, pErrCode) : TRUE ;
	if (ret) {
	    BitStream_AppendBit(pBitStrm,pVal->exist.a);
	    if (ret) {
	        BitStream_AppendBit(pBitStrm,pVal->exist.d);
	        if (ret) {
	            /*Encode a */
	            if (pVal->exist.a) {
	            	BitStream_AppendBit(pBitStrm,pVal->a);
	            }
	            if (ret) {
	                /*Encode b */
	                BitStream_EncodeConstraintPosWholeNumber(pBitStrm, pVal->b, 0, 1299);
	                if (ret) {
	                    /*Encode c */
	                    BitStream_EncodeConstraintPosWholeNumber(pBitStrm, pVal->c, 0, 255);
	                    if (ret) {
	                        /*Encode d */
	                        if (pVal->exist.d) {
	                        	ret = T_TypeThatMustNotBeMappedExceptInPython_Encode((&(pVal->d)), pBitStrm, pErrCode, FALSE);
	                        }
	                    }
	                }
	            }
	        }
	    }
    } /*COVERAGE_IGNORE*/

	
    return ret;
}


flag SubTypeWithOptional_Equal(const SubTypeWithOptional* pVal1, const SubTypeWithOptional* pVal2)
{
	flag ret=TRUE;

    ret = TypeWithOptional_Equal(pVal1, pVal2);
	return ret;
}


flag SuperChoice_second_choice_Equal(const SuperChoice_second_choice* pVal1, const SuperChoice_second_choice* pVal2)
{
	(void)pVal1;
	(void)pVal2;

	return (*(pVal1)) == (*(pVal2));

}

void SuperChoice_second_choice_Initialize(SuperChoice_second_choice* pVal)
{
	(void)pVal;


	(*(pVal)) = 0;
}


flag E_Equal(const E* pVal1, const E* pVal2)
{
	(void)pVal1;
	(void)pVal2;

	return (*(pVal1)) == (*(pVal2));

}



flag MyInt_Equal(const MyInt* pVal1, const MyInt* pVal2)
{
	(void)pVal1;
	(void)pVal2;

	return (*(pVal1)) == (*(pVal2));

}

flag My2ndInt_Equal(const My2ndInt* pVal1, const My2ndInt* pVal2)
{
	(void)pVal1;
	(void)pVal2;

	return (*(pVal1)) == (*(pVal2));

}


flag AType_blArray_Equal(const AType_blArray* pVal1, const AType_blArray* pVal2)
{
	(void)pVal1;
	(void)pVal2;

	flag ret=TRUE;
    int i1;

    for(i1 = 0; ret && i1 < 10; i1++)
    {
    	ret = (pVal1->arr[i1] == pVal2->arr[i1]);
    }

	return ret;

}

flag AType_Equal(const AType* pVal1, const AType* pVal2)
{
	(void)pVal1;
	(void)pVal2;

	flag ret=TRUE;

    ret = AType_blArray_Equal((&(pVal1->blArray)), (&(pVal2->blArray)));

	return ret;

}

flag My2ndAType_Equal(const My2ndAType* pVal1, const My2ndAType* pVal2)
{
	flag ret=TRUE;

    ret = AType_Equal(pVal1, pVal2);
	return ret;
}

void My2ndAType_Initialize(My2ndAType* pVal)
{
	(void)pVal;


	AType_Initialize(pVal);
}


flag T_ARR_elem_Equal(const T_ARR_elem* pVal1, const T_ARR_elem* pVal2)
{
	(void)pVal1;
	(void)pVal2;

	return (*(pVal1)) == (*(pVal2));

}

flag T_ARR_Equal(const T_ARR* pVal1, const T_ARR* pVal2)
{
	(void)pVal1;
	(void)pVal2;

	flag ret=TRUE;
    int i1;

    ret = (pVal1->nCount == pVal2->nCount);
    for(i1 = 0; ret && i1 < pVal1->nCount; i1++)
    {
    	ret = T_ARR_elem_Equal((&(pVal1->arr[i1])), (&(pVal2->arr[i1])));
    }

	return ret;

}

void My2ndArr_Initialize(My2ndArr* pVal)
{
	(void)pVal;


	T_ARR_Initialize(pVal);
}


flag T_ARR3_elem_Equal(const T_ARR3_elem* pVal1, const T_ARR3_elem* pVal2)
{
	(void)pVal1;
	(void)pVal2;

	flag ret=TRUE;
    int i2;

    for(i2 = 0; ret && i2 < 7; i2++)
    {
    	ret = (pVal1->arr[i2] == pVal2->arr[i2]);
    }

	return ret;

}

void T_ARR3_Initialize(T_ARR3* pVal)
{
	(void)pVal;

    int i1;

	i1 = 0;
	while (i1< 6) {
	    T_ARR3_elem_Initialize((&(pVal->arr[i1])));
	    i1 = i1 + 1;
	}
	pVal->nCount = 5;
}

void T_SET_Initialize(T_SET* pVal)
{
	(void)pVal;



	/*set data1 */
	T_SET_data1_Initialize((&(pVal->data1)));
	/*set data2 */
	pVal->data2 = 0.00000000000000000000E+000;
	/*set data3 */
	T_SET_data3_Initialize((&(pVal->data3)));
	/*set data4 */
	T_SET_data4_Initialize((&(pVal->data4)));
}

flag T_SET_IsConstraintValid(const T_SET* pVal, int* pErrCode)
{
    flag ret = TRUE;
	(void)pVal;

    ret = (pVal->data1 <= 131071UL);
    *pErrCode = ret ? 0 :  ERR_T_SET_DATA1;
    if (ret) {
        ret = ((-1.00000000000000000000E+002 <= pVal->data2) && (pVal->data2 <= 1.00000000000000000000E+001));
        *pErrCode = ret ? 0 :  ERR_T_SET_DATA2;
        if (ret) {
            ret = ((-1024LL <= pVal->data3) && (pVal->data3 <= 1024LL));
            *pErrCode = ret ? 0 :  ERR_T_SET_DATA3;
            if (ret) {
                ret = ((-1310720LL <= pVal->data4) && (pVal->data4 <= 131071LL));
                *pErrCode = ret ? 0 :  ERR_T_SET_DATA4;
            }
        }
    }

	return ret;
}

flag T_SETOF_Encode(const T_SETOF* pVal, BitStream* pBitStrm, int* pErrCode, flag bCheckConstraints)
{

    return ret;
}

flag My2ndBool_Encode(const My2ndBool* pVal, BitStream* pBitStrm, int* pErrCode, flag bCheckConstraints)
{
    flag ret = TRUE;
	(void)pVal;
	(void)pBitStrm;


	ret = bCheckConstraints ? My2ndBool_IsConstraintValid(pVal, pErrCode) : TRUE ;
	if (ret) {
	    ret = T_BOOL_Encode(pVal, pBitStrm, pErrCode, FALSE);
    } /*COVERAGE_IGNORE*/


    return ret;
}

flag T_INT_IsConstraintValid(const T_INT* pVal, int* pErrCode)
{
    flag ret = TRUE;
	(void)pVal;

    ret = ((*(pVal)) <= 50UL);
    *pErrCode = ret ? 0 :  ERR_T_INT;

	return ret;
}


flag T_REAL_Equal(const T_REAL* pVal1, const T_REAL* pVal2)
{
	(void)pVal1;
	(void)pVal2;

	return (*(pVal1)) == (*(pVal2));

}

flag T_STRING_IsConstraintValid(const T_STRING* pVal, int* pErrCode)
{
    flag ret = TRUE;
	(void)pVal;

    ret = ((10 <= pVal->nCount) && (pVal->nCount <= 15));
    *pErrCode = ret ? 0 :  ERR_T_STRING;

	return ret;
}

flag TypeNested_int2Val_Equal(const TypeNested_int2Val* pVal1, const TypeNested_int2Val* pVal2)
{
	(void)pVal1;
	(void)pVal2;

	return (*(pVal1)) == (*(pVal2));

}

flag TypeNested_boolArray_Equal(const TypeNested_boolArray* pVal1, const TypeNested_boolArray* pVal2)
{
	(void)pVal1;
	(void)pVal2;

	flag ret=TRUE;
    int i1;

    for(i1 = 0; ret && i1 < 10; i1++)
    {
    	ret = (pVal1->arr[i1] == pVal2->arr[i1]);
    }

	return ret;

}

flag T_POS_Decode(T_POS* pVal, BitStream* pBitStrm, int* pErrCode)
{
    flag ret = TRUE;
	*pErrCode = 0;
	(void)pVal;
	(void)pBitStrm;


	return ret  && T_POS_IsConstraintValid(pVal, pErrCode);
}



flag T_META_Equal(const T_META* pVal1, const T_META* pVal2)
{
	flag ret=TRUE;

    ret = T_POS_Equal(pVal1, pVal2);
	return ret;
}

flag T_POS_SET_subTypeArray_Equal(const T_POS_SET_subTypeArray* pVal1, const T_POS_SET_subTypeArray* pVal2)
{
	(void)pVal1;
	(void)pVal2;

	flag ret=TRUE;
    int i1;

    ret = (pVal1->nCount == pVal2->nCount);
    for(i1 = 0; ret && i1 < pVal1->nCount; i1++)
    {
    	ret = TypeNested_Equal((&(pVal1->arr[i1])), (&(pVal2->arr[i1])));
    }

	return ret;

}


flag My2ndString_Equal(const My2ndString* pVal1, const My2ndString* pVal2)
{
	flag ret=TRUE;

    ret = T_STRING_Equal(pVal1, pVal2);
	return ret;
}

void ConfigString_Initialize(ConfigString val)
{
	(void)val;


	memset(val, 0x0, 21);

}


flag AType_Encode(const AType* pVal, BitStream* pBitStrm, int* pErrCode, flag bCheckConstraints)
{
    flag ret = TRUE;
	(void)pVal;
	(void)pBitStrm;


	int i1;
	ret = bCheckConstraints ? AType_IsConstraintValid(pVal, pErrCode) : TRUE ;
	if (ret) {
	    /*Encode blArray */

	    for(i1=0; (i1 < (int)10) && ret; i1++)
	    {
	    	BitStream_AppendBit(pBitStrm,pVal->blArray.arr[i1]);
	    }
    } /*COVERAGE_IGNORE*/


    return ret;
}